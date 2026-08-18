"""Structured AI Director plan. Validated JSON, never a free-text blob."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

VisualType = Literal["stock", "ai_image", "ai_video", "user_asset"]
VisualMode = Literal["auto", "stock", "ai_video", "mixed"]


class ScenePlan(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    order: int = Field(ge=1, le=40)
    duration: float = Field(ge=2, le=20)
    narration: str = Field(min_length=1, max_length=2000)
    visual_type: VisualType = "stock"
    visual_prompt: str = Field(default="", max_length=2000)
    visual_query: str = Field(default="", max_length=200)
    caption: str = Field(default="", max_length=400)
    transition: str = Field(default="cut", max_length=40)
    camera_motion: str = Field(default="static", max_length=80)
    generation_provider: str = Field(default="", max_length=40)
    generation_model: str = Field(default="", max_length=120)
    voice_style: str = Field(default="", max_length=80)
    music_hint: str = Field(default="", max_length=80)
    asset_id: str | None = None

    @field_validator("visual_type", mode="before")
    @classmethod
    def _visual_type(cls, value: object) -> str:
        raw = str(value or "stock").strip().lower().replace("-", "_")
        aliases = {"pexels": "stock", "image": "ai_image", "video": "ai_video", "asset": "user_asset"}
        raw = aliases.get(raw, raw)
        if raw not in {"stock", "ai_image", "ai_video", "user_asset"}:
            return "stock"
        return raw


class VideoPlan(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    hook: str = Field(default="", max_length=400)
    description: str = Field(default="", max_length=2000)
    duration: int = Field(default=30, ge=5, le=300)
    language: str = Field(default="en-US", max_length=32)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    resolution: Literal["1080p", "720p"] = "1080p"
    style: str = Field(default="cinematic", max_length=80)
    tone: str = Field(default="informative", max_length=80)
    target_platform: str = Field(default="short", max_length=40)
    visual_mode: VisualMode = "auto"
    music_style: str = Field(default="cinematic", max_length=80)
    scenes: list[ScenePlan] = Field(default_factory=list, min_length=1, max_length=20)

    @field_validator("visual_mode", mode="before")
    @classmethod
    def _mode(cls, value: object) -> str:
        raw = str(value or "auto").strip().lower().replace(" ", "_")
        aliases = {"stock_only": "stock", "ai": "ai_video", "ai-video": "ai_video"}
        raw = aliases.get(raw, raw)
        if raw not in {"auto", "stock", "ai_video", "mixed"}:
            return "auto"
        return raw
