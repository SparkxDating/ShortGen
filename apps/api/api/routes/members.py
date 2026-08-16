from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.member import (
    InviteAccept,
    InviteCreate,
    InvitePreview,
    InviteResponse,
    MemberResponse,
    MemberRoleUpdate,
)
from apps.api.services import member_service

router = APIRouter()


@router.get("/workspaces/{workspace_id}/members", response_model=list[MemberResponse])
def list_members(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MemberResponse]:
    return member_service.list_members(db, workspace_id, current_user.id)


@router.patch("/workspaces/{workspace_id}/members/{user_id}", response_model=MemberResponse)
def update_member(
    workspace_id: str,
    user_id: str,
    payload: MemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberResponse:
    return member_service.update_member_role(db, workspace_id, user_id, current_user.id, payload.role)


@router.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    member_service.remove_member(db, workspace_id, user_id, current_user.id)


@router.get("/workspaces/{workspace_id}/invites", response_model=list[InviteResponse])
def list_invites(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InviteResponse]:
    return member_service.list_invites(db, workspace_id, current_user.id)


@router.post(
    "/workspaces/{workspace_id}/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invite(
    workspace_id: str,
    payload: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteResponse:
    return member_service.create_invite(db, workspace_id, current_user.id, payload.email, payload.role)


@router.delete(
    "/workspaces/{workspace_id}/invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_invite(
    workspace_id: str,
    invite_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    member_service.revoke_invite(db, workspace_id, invite_id, current_user.id)


@router.get("/invites/{token}", response_model=InvitePreview)
def preview_invite(token: str, db: Session = Depends(get_db)) -> InvitePreview:
    workspace_name, invite = member_service.preview_invite(db, token)
    return InvitePreview(
        workspace_name=workspace_name,
        email=invite.email,
        role=invite.role,
        status=invite.status,
    )


@router.post("/invites/accept", response_model=MemberResponse)
def accept_invite(
    payload: InviteAccept,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberResponse:
    return member_service.accept_invite(db, payload.token, current_user)
