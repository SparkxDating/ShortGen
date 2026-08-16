from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from apps.api.services import workspace_service

router = APIRouter()


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkspaceResponse]:
    rows = workspace_service.list_workspaces(db, current_user.id)
    return [
        WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            owner_id=workspace.owner_id,
            role=membership.role,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        for workspace, membership in rows
    ]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace = workspace_service.create_workspace(db, current_user, payload.name)
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        owner_id=workspace.owner_id,
        role="owner",
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )
