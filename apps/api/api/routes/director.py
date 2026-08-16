"""AI Director routes. Planning only — rendering stays on the existing engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.common import ORMModel
from apps.api.services import script_service
from ai_engine.providers import list_providers

router = APIRouter()


class DirectorPlanRequest(ORMModel):
    workspace_id: str
    topic: str = Field(min_length=1, max_length=500)
    video_language: str = Field(default="en-US", max_length=32)


class DirectorPlanResponse(ORMModel):
    topic: str
    script: str
    plan: str
    renderer: str = "moneyprinterturbo"


@router.get("/providers")
def providers(current_user: User = Depends(get_current_user)) -> list[dict]:
    return list_providers()


@router.post("/plan", response_model=DirectorPlanResponse)
def plan(
    payload: DirectorPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DirectorPlanResponse:
    preview = script_service.preview_script(
        db,
        current_user.id,
        payload.workspace_id,
        payload.topic,
        payload.video_language,
    )
    plan_text = (
        f"Hook\n{payload.topic.strip()}\n\n"
        f"Narration\n{preview.script}\n\n"
        "Visuals\nStock or library clips matching the narration.\n\n"
        "Renderer\nExisting ShortGen engine (MoneyPrinterTurbo). Extra AI video providers are listed but not wired."
    )
    return DirectorPlanResponse(topic=payload.topic.strip(), script=preview.script, plan=plan_text)
