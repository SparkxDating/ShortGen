from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.models.user import User
from apps.api.models.workspace import ROLE_RANK, Workspace, WorkspaceMember, WorkspaceRole
from apps.api.services.errors import ConflictError, ForbiddenError, NotFoundError


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)[:80]
    candidate = base
    while db.scalar(select(Workspace.id).where(Workspace.slug == candidate)):
        candidate = f"{base}-{uuid4().hex[:6]}"
    return candidate


def get_membership(db: Session, workspace_id: str, user_id: str) -> WorkspaceMember | None:
    return db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )


def require_membership(
    db: Session,
    workspace_id: str,
    user_id: str,
    minimum: WorkspaceRole = WorkspaceRole.viewer,
) -> WorkspaceMember:
    membership = get_membership(db, workspace_id, user_id)
    if membership is None:
        # Hide existence of foreign workspaces.
        raise NotFoundError("workspace not found")
    try:
        role = WorkspaceRole(membership.role)
    except ValueError as exc:
        raise ForbiddenError("invalid workspace role") from exc
    if ROLE_RANK[role] < ROLE_RANK[minimum]:
        raise ForbiddenError("insufficient workspace role")
    return membership


def create_workspace(db: Session, owner: User, name: str) -> Workspace:
    workspace = Workspace(name=name.strip(), slug=unique_slug(db, name), owner_id=owner.id)
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner.id,
            role=WorkspaceRole.owner.value,
        )
    )
    db.flush()
    from apps.api.services import credit_service

    credit_service.provision_workspace(db, workspace.id, owner.id)
    from apps.api.models.project import Project

    db.add(
        Project(
            workspace_id=workspace.id,
            name="My First Project",
            description="Created automatically so you can generate a video right away.",
            created_by=owner.id,
        )
    )
    db.flush()
    return workspace


def list_workspaces(db: Session, user_id: str) -> list[tuple[Workspace, WorkspaceMember]]:
    rows = db.execute(
        select(Workspace, WorkspaceMember)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at.desc())
    ).all()
    return [(workspace, membership) for workspace, membership in rows]


def get_accessible_workspace(db: Session, workspace_id: str, user_id: str) -> Workspace:
    membership = require_membership(db, workspace_id, user_id)
    workspace = db.get(Workspace, membership.workspace_id)
    if workspace is None:
        raise NotFoundError("workspace not found")
    return workspace
