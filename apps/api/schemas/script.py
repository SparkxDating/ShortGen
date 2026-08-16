from __future__ import annotations

from pydantic import Field

from apps.api.schemas.common import ORMModel


class ScriptPreviewRequest(ORMModel):
    workspace_id: str
    topic: str = Field(min_length=1, max_length=500)
    video_language: str = Field(default="en-US", max_length=32)
    paragraph_number: int = Field(default=1, ge=1, le=6)


class ScriptPreviewResponse(ORMModel):
    script: str
    topic: str
    video_language: str
