from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.template import TemplateCreate, TemplateResponse
from apps.api.services import template_service

router = APIRouter()


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    workspace_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TemplateResponse]:
    return template_service.list_templates(db, current_user.id, workspace_id)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    return template_service.create_template(db, current_user.id, payload)


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    return TemplateResponse.model_validate(
        template_service.get_template(db, template_id, current_user.id)
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    template_service.delete_template(db, template_id, current_user.id)
