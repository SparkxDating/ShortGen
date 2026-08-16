"""Script preview uses the existing MoneyPrinterTurbo LLM path via the adapter."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.script import ScriptPreviewResponse
from apps.api.services import workspace_service
from apps.api.services.errors import ServiceError
from video_engine.generation_adapter import GenerationError, MoneyPrinterTurboGenerationAdapter


def preview_script(
    db: Session,
    user_id: str,
    workspace_id: str,
    topic: str,
    video_language: str,
    paragraph_number: int = 1,
) -> ScriptPreviewResponse:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.editor)
    adapter = MoneyPrinterTurboGenerationAdapter()
    try:
        params = adapter.build_params(
            {
                "topic": topic,
                "video_language": video_language,
                "paragraph_number": paragraph_number,
            }
        )
        script = adapter.generate_script(f"preview-{uuid4().hex}", params)
    except GenerationError as exc:
        raise ServiceError(str(exc), status_code=502) from exc
    except Exception as exc:
        raise ServiceError(
            "script preview is unavailable; check LLM configuration in config.toml",
            status_code=503,
        ) from exc
    return ScriptPreviewResponse(script=script, topic=topic, video_language=video_language)
