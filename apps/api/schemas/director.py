from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from apps.api.schemas.common import ORMModel


class DirectorPlanRequest(ORMModel):
    workspace_id: str
    topic: str = Field(min_length=1, max_length=500)
    video_language: str = Field(default="en-US", max_length=32)
    duration: int = Field(default=30, ge=5, le=300)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    resolution: Literal["1080p", "720p"] = "1080p"
    style: str = Field(default="cinematic", max_length=80)
    tone: str = Field(default="informative", max_length=80)
    target_platform: str = Field(default="short", max_length=40)
    visual_mode: Literal["auto", "stock", "ai_video", "mixed"] = "auto"
    project_id: str | None = None
    asset_ids: list[str] = Field(default_factory=list)


class ScenePlanOut(ORMModel):
    id: str
    order: int
    duration: float
    narration: str
    visual_type: str
    visual_prompt: str
    visual_query: str
    caption: str
    camera_motion: str = "static"
    generation_provider: str = ""
    generation_model: str = ""
    asset_id: str | None = None


class VideoPlanOut(ORMModel):
    title: str
    hook: str = ""
    description: str = ""
    duration: int
    language: str
    aspect_ratio: str
    resolution: str
    style: str
    tone: str
    target_platform: str
    visual_mode: str
    music_style: str = "cinematic"
    scenes: list[ScenePlanOut]


class DirectorPlanResponse(ORMModel):
    topic: str
    script: str
    plan: str
    renderer: str = "moneyprinterturbo"
    video_plan: VideoPlanOut
    video_id: str | None = None
    source: str = "local"
    warning: str = ""


class ScenePatch(ORMModel):
    narration: str | None = Field(default=None, max_length=2000)
    visual_type: Literal["stock", "ai_image", "ai_video", "user_asset"] | None = None
    visual_prompt: str | None = Field(default=None, max_length=2000)
    visual_query: str | None = Field(default=None, max_length=200)
    duration: float | None = Field(default=None, ge=2, le=20)
    asset_id: str | None = None


class SceneResponse(ORMModel):
    id: str
    video_id: str
    order: int
    duration: float
    narration: str
    visual_type: str
    visual_prompt: str
    visual_query: str
    caption: str
    provider: str
    provider_job_id: str | None = None
    status: str
    progress: int
    asset_id: str | None = None
    error_message: str | None = None


class CapabilitiesResponse(ORMModel):
    ai_video: bool
    ai_image: bool
    message: str = ""
    providers: list[dict[str, Any]] = Field(default_factory=list)
