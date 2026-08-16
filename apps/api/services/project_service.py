from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.models.project import Project
from apps.api.models.workspace import WorkspaceRole
from apps.api.services import workspace_service
from apps.api.services.errors import NotFoundError


def list_projects(db: Session, user_id: str, workspace_id: str | None = None) -> list[Project]:
    query = select(Project)
    if workspace_id:
        workspace_service.require_membership(db, workspace_id, user_id)
        query = query.where(Project.workspace_id == workspace_id)
    else:
        memberships = workspace_service.list_workspaces(db, user_id)
        ids = [workspace.id for workspace, _ in memberships]
        if not ids:
            return []
        query = query.where(Project.workspace_id.in_(ids))
    return list(db.scalars(query.order_by(Project.updated_at.desc())).all())


def ensure_default_project(db: Session, user_id: str, workspace_id: str) -> Project:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.editor)
    existing = db.scalar(
        select(Project).where(Project.workspace_id == workspace_id).order_by(Project.created_at.asc())
    )
    if existing:
        return existing
    return create_project(db, user_id, workspace_id, "My First Project", "Created automatically.")


def get_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("project not found")
    workspace_service.require_membership(db, project.workspace_id, user_id)
    return project


def create_project(
    db: Session,
    user_id: str,
    workspace_id: str,
    name: str,
    description: str = "",
) -> Project:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.editor)
    project = Project(
        workspace_id=workspace_id,
        name=name.strip(),
        description=description.strip() or None,
        created_by=user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: str, user_id: str) -> None:
    project = get_project(db, project_id, user_id)
    workspace_service.require_membership(db, project.workspace_id, user_id, WorkspaceRole.admin)
    db.delete(project)
    db.commit()
