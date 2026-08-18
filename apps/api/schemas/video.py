from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from apps.api.schemas.common import ORMModel
from apps.api.schemas.job import JobResponse


class VideoCreate(ORMModel):
    workspace_id: str
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=500)
    video_language: str = Field(default="en-US", max_length=32)
    duration: int = Field(default=30, ge=5, le=300)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    resolution: Literal["1080p", "720p"] = "1080p"
    voice: str = Field(default="en-US-JennyNeural-Female", max_length=120)
    visual_source: Literal["stock", "local"] = "stock"
    video_script: str = Field(default="", max_length=20000)
    subtitle_enabled: bool = True
    video_clip_duration: int = Field(default=3, ge=2, le=8)
    match_materials_to_script: bool = True
    video_concat_mode: Literal["sequential", "random"] = "sequential"
    asset_ids: list[str] = Field(default_factory=list)
    template_id: str | None = None


class VideoResponse(ORMModel):
    id: str
    workspace_id: str
    project_id: str
    title: str
    status: str
    progress: int
    duration: float | None = None
    aspect_ratio: str
    resolution: str
    thumbnail_url: str | None = None
    video_url: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime | None = None
    latest_job: JobResponse | None = None
