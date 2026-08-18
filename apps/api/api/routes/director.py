"""AI Director routes. Planning only — rendering stays on the existing engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ai_engine.providers import list_providers
from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.director import DirectorPlanRequest, DirectorPlanResponse
from apps.api.services import director_service

router = APIRouter()


@router.get("/providers")
def providers(current_user: User = Depends(get_current_user)) -> list[dict]:
    return list_providers()


@router.post("/plan", response_model=DirectorPlanResponse)
def plan(
    payload: DirectorPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DirectorPlanResponse:
    return director_service.create_plan(db, current_user.id, payload)
