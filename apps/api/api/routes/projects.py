from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.project import ProjectCreate, ProjectResponse
from apps.api.services import project_service

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    workspace_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectResponse]:
    projects = project_service.list_projects(db, current_user.id, workspace_id)
    return [ProjectResponse.model_validate(project) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = project_service.create_project(
        db,
        current_user.id,
        payload.workspace_id,
        payload.name,
        payload.description,
    )
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return ProjectResponse.model_validate(project_service.get_project(db, project_id, current_user.id))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project_service.delete_project(db, project_id, current_user.id)
