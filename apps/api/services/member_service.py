from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.models.invite import InviteStatus, WorkspaceInvite
from apps.api.models.user import User
from apps.api.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from apps.api.schemas.member import InviteResponse, MemberResponse
from apps.api.services import workspace_service
from apps.api.services.errors import ConflictError, ForbiddenError, NotFoundError, ServiceError

INVITE_TTL = timedelta(days=7)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def list_members(db: Session, workspace_id: str, user_id: str) -> list[MemberResponse]:
    workspace_service.require_membership(db, workspace_id, user_id)
    rows = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at.asc())
    ).all()
    return [
        MemberResponse(
            id=member.id,
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=member.role,
            created_at=member.created_at,
        )
        for member, user in rows
    ]


def _owner_count(db: Session, workspace_id: str) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.owner.value,
            )
        )
        or 0
    )


def update_member_role(
    db: Session,
    workspace_id: str,
    target_user_id: str,
    actor_id: str,
    role: str,
) -> MemberResponse:
    actor = workspace_service.require_membership(db, workspace_id, actor_id, WorkspaceRole.admin)
    membership = workspace_service.get_membership(db, workspace_id, target_user_id)
    if membership is None:
        raise NotFoundError("member not found")
    if role == WorkspaceRole.owner.value and WorkspaceRole(actor.role) != WorkspaceRole.owner:
        raise ForbiddenError("only an owner can assign the owner role")
    if (
        membership.role == WorkspaceRole.owner.value
        and role != WorkspaceRole.owner.value
        and _owner_count(db, workspace_id) <= 1
    ):
        raise ForbiddenError("a workspace must keep at least one owner")
    membership.role = role
    if role == WorkspaceRole.owner.value:
        workspace = db.get(Workspace, workspace_id)
        if workspace:
            workspace.owner_id = target_user_id
    db.commit()
    user = db.get(User, target_user_id)
    assert user is not None
    return MemberResponse(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=membership.role,
        created_at=membership.created_at,
    )


def remove_member(db: Session, workspace_id: str, target_user_id: str, actor_id: str) -> None:
    workspace_service.require_membership(db, workspace_id, actor_id, WorkspaceRole.admin)
    membership = workspace_service.get_membership(db, workspace_id, target_user_id)
    if membership is None:
        raise NotFoundError("member not found")
    if membership.role == WorkspaceRole.owner.value and _owner_count(db, workspace_id) <= 1:
        raise ForbiddenError("cannot remove the last owner")
    db.delete(membership)
    db.commit()


def create_invite(
    db: Session,
    workspace_id: str,
    actor_id: str,
    email: str,
    role: str,
) -> InviteResponse:
    workspace_service.require_membership(db, workspace_id, actor_id, WorkspaceRole.admin)
    if role == WorkspaceRole.owner.value:
        raise ForbiddenError("invite as admin, then transfer ownership")
    normalized = email.lower().strip()
    existing_user = db.scalar(select(User).where(User.email == normalized))
    if existing_user and workspace_service.get_membership(db, workspace_id, existing_user.id):
        raise ConflictError("user is already a workspace member")
    pending = db.scalar(
        select(WorkspaceInvite).where(
            WorkspaceInvite.workspace_id == workspace_id,
            WorkspaceInvite.email == normalized,
            WorkspaceInvite.status == InviteStatus.pending.value,
        )
    )
    if pending:
        raise ConflictError("an invite is already pending for this email")
    invite = WorkspaceInvite(
        workspace_id=workspace_id,
        email=normalized,
        role=role,
        token=secrets.token_urlsafe(32),
        invited_by=actor_id,
        status=InviteStatus.pending.value,
        expires_at=datetime.now(timezone.utc) + INVITE_TTL,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return InviteResponse.model_validate(invite)


def list_invites(db: Session, workspace_id: str, user_id: str) -> list[InviteResponse]:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.admin)
    invites = list(
        db.scalars(
            select(WorkspaceInvite)
            .where(WorkspaceInvite.workspace_id == workspace_id)
            .order_by(WorkspaceInvite.created_at.desc())
        ).all()
    )
    return [InviteResponse.model_validate(invite) for invite in invites]


def revoke_invite(db: Session, workspace_id: str, invite_id: str, user_id: str) -> None:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.admin)
    invite = db.get(WorkspaceInvite, invite_id)
    if invite is None or invite.workspace_id != workspace_id:
        raise NotFoundError("invite not found")
    invite.status = InviteStatus.revoked.value
    db.commit()


def preview_invite(db: Session, token: str) -> tuple[str, WorkspaceInvite]:
    invite = db.scalar(select(WorkspaceInvite).where(WorkspaceInvite.token == token))
    if invite is None:
        raise NotFoundError("invite not found")
    workspace = db.get(Workspace, invite.workspace_id)
    if workspace is None:
        raise NotFoundError("invite not found")
    if invite.status == InviteStatus.pending.value and _aware(invite.expires_at) < datetime.now(timezone.utc):
        invite.status = InviteStatus.expired.value
        db.commit()
    return workspace.name, invite


def accept_invite(db: Session, token: str, user: User) -> MemberResponse:
    workspace_name, invite = preview_invite(db, token)
    del workspace_name
    if invite.status != InviteStatus.pending.value:
        raise ServiceError(f"invite is {invite.status}", status_code=409)
    if invite.email != user.email.lower().strip():
        raise ForbiddenError("this invite was sent to a different email address")
    if workspace_service.get_membership(db, invite.workspace_id, user.id):
        invite.status = InviteStatus.accepted.value
        db.commit()
        membership = workspace_service.get_membership(db, invite.workspace_id, user.id)
        assert membership is not None
        return MemberResponse(
            id=membership.id,
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=membership.role,
            created_at=membership.created_at,
        )
    membership = WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=user.id,
        role=invite.role,
    )
    db.add(membership)
    invite.status = InviteStatus.accepted.value
    db.commit()
    db.refresh(membership)
    return MemberResponse(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=membership.role,
        created_at=membership.created_at,
    )
