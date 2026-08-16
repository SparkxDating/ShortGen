from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from apps.api.models.template import Template
from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.template import TemplateCreate, TemplateResponse
from apps.api.services import workspace_service
from apps.api.services.errors import ForbiddenError, NotFoundError

SYSTEM_TEMPLATES = [
    {
        "name": "Viral Short",
        "description": "Vertical 30-second hook for Reels, Shorts, and TikTok.",
        "config": {
            "duration": 30,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "voice": "en-US-JennyNeural-Female",
            "visual_source": "stock",
            "subtitle_enabled": True,
        },
    },
    {
        "name": "Explainer",
        "description": "Landscape walkthrough for YouTube or a landing page.",
        "config": {
            "duration": 60,
            "aspect_ratio": "16:9",
            "resolution": "1080p",
            "voice": "en-US-GuyNeural-Male",
            "visual_source": "stock",
            "subtitle_enabled": True,
        },
    },
    {
        "name": "Product Teaser",
        "description": "Square teaser for ads and social feeds.",
        "config": {
            "duration": 20,
            "aspect_ratio": "1:1",
            "resolution": "1080p",
            "voice": "en-US-JennyNeural-Female",
            "visual_source": "stock",
            "subtitle_enabled": True,
        },
    },
    {
        "name": "News Brief",
        "description": "Fast-paced vertical briefing.",
        "config": {
            "duration": 45,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "voice": "en-US-GuyNeural-Male",
            "visual_source": "stock",
            "subtitle_enabled": True,
        },
    },
    {
        "name": "Tutorial Clip",
        "description": "Longer landscape how-to with captions.",
        "config": {
            "duration": 90,
            "aspect_ratio": "16:9",
            "resolution": "1080p",
            "voice": "en-US-JennyNeural-Female",
            "visual_source": "local",
            "subtitle_enabled": True,
        },
    },
    {
        "name": "Quote Card",
        "description": "Short spoken quote over stock footage.",
        "config": {
            "duration": 15,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "voice": "en-US-JennyNeural-Female",
            "visual_source": "stock",
            "subtitle_enabled": True,
        },
    },
]


def seed_system_templates(db: Session) -> None:
    existing = db.scalar(select(Template.id).where(Template.is_system.is_(True)).limit(1))
    if existing:
        return
    for item in SYSTEM_TEMPLATES:
        db.add(
            Template(
                workspace_id=None,
                name=item["name"],
                description=item["description"],
                is_system=True,
                config=item["config"],
                created_by=None,
            )
        )
    db.commit()


def list_templates(db: Session, user_id: str, workspace_id: str | None = None) -> list[TemplateResponse]:
    if workspace_id:
        workspace_service.require_membership(db, workspace_id, user_id)
        query = select(Template).where(
            or_(Template.is_system.is_(True), Template.workspace_id == workspace_id)
        )
    else:
        memberships = workspace_service.list_workspaces(db, user_id)
        ids = [workspace.id for workspace, _ in memberships]
        if ids:
            query = select(Template).where(
                or_(Template.is_system.is_(True), Template.workspace_id.in_(ids))
            )
        else:
            query = select(Template).where(Template.is_system.is_(True))
    templates = list(db.scalars(query.order_by(Template.is_system.desc(), Template.name.asc())).all())
    return [TemplateResponse.model_validate(item) for item in templates]


def get_template(db: Session, template_id: str, user_id: str) -> Template:
    template = db.get(Template, template_id)
    if template is None:
        raise NotFoundError("template not found")
    if template.is_system or template.workspace_id is None:
        return template
    workspace_service.require_membership(db, template.workspace_id, user_id)
    return template


def create_template(db: Session, user_id: str, payload: TemplateCreate) -> TemplateResponse:
    workspace_service.require_membership(db, payload.workspace_id, user_id, WorkspaceRole.editor)
    template = Template(
        workspace_id=payload.workspace_id,
        name=payload.name.strip(),
        description=payload.description.strip() or None,
        is_system=False,
        config=payload.config or {},
        created_by=user_id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return TemplateResponse.model_validate(template)


def delete_template(db: Session, template_id: str, user_id: str) -> None:
    template = get_template(db, template_id, user_id)
    if template.is_system:
        raise ForbiddenError("system templates cannot be deleted")
    assert template.workspace_id is not None
    workspace_service.require_membership(db, template.workspace_id, user_id, WorkspaceRole.admin)
    db.delete(template)
    db.commit()
