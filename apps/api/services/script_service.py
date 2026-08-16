"""Script preview uses the existing MoneyPrinterTurbo LLM path via the adapter."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.script import ScriptPreviewResponse
from apps.api.services import workspace_service
from apps.api.services.local_script import write_script
from video_engine.generation_adapter import GenerationError, MoneyPrinterTurboGenerationAdapter

logger = logging.getLogger("saas.script")


def preview_script(
    db: Session,
    user_id: str,
    workspace_id: str,
    topic: str,
    video_language: str,
    paragraph_number: int = 1,
) -> ScriptPreviewResponse:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.editor)
    script = ""
    if _llm_configured():
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
        except (GenerationError, Exception) as exc:
            logger.warning("LLM script preview unavailable (%s); using local draft", exc)
            script = ""
    if not script or str(script).startswith("Error:"):
        script = write_script(topic, video_language)
    return ScriptPreviewResponse(script=script, topic=topic, video_language=video_language)


def _llm_configured() -> bool:
    import os

    if os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return True
    try:
        from app.config import config

        provider = str(config.app.get("llm_provider") or "")
        key_name = f"{provider}_api_key" if provider else "openai_api_key"
        return bool(str(config.app.get(key_name) or "").strip())
    except Exception:
        return False
