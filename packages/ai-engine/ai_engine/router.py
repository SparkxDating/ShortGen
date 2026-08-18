"""Authorize and select visual providers. Users cannot pass arbitrary URLs."""

from __future__ import annotations

import os

from ai_engine.image.mock import MockAIImageProvider
from ai_engine.image.replicate import ReplicateImageProvider
from ai_engine.types import ProviderCapabilities
from ai_engine.video.mock import MockAIVideoProvider
from ai_engine.video.replicate import ReplicateVideoProvider

ALLOWED_VIDEO = {"replicate", "mock"}
ALLOWED_IMAGE = {"replicate", "mock"}


class ProviderNotAllowed(ValueError):
    pass


class AIProviderRouter:
    def __init__(
        self,
        *,
        environment: str = "development",
        video_provider: str | None = None,
        image_provider: str | None = None,
        video_enabled: bool = True,
    ) -> None:
        self.environment = environment
        self.video_enabled = video_enabled
        self._video_name = (video_provider or os.getenv("AI_VIDEO_PROVIDER") or "replicate").strip().lower()
        self._image_name = (image_provider or os.getenv("AI_IMAGE_PROVIDER") or "replicate").strip().lower()
        if self.environment.lower() in {"test", "ci"}:
            self._video_name = "mock"
            self._image_name = "mock"

    def select_video_provider(self, requested: str | None = None):
        if not self.video_enabled:
            raise ProviderNotAllowed("AI video generation is temporarily unavailable")
        name = (requested or self._video_name or "replicate").strip().lower()
        if name not in ALLOWED_VIDEO:
            raise ProviderNotAllowed(f"video provider is not allowed: {name}")
        if name == "mock":
            if self.environment.lower() in {"prod", "production"}:
                raise ProviderNotAllowed("mock video provider is not available in production")
            return MockAIVideoProvider()
        return ReplicateVideoProvider()

    def select_image_provider(self, requested: str | None = None):
        name = (requested or self._image_name or "replicate").strip().lower()
        if name not in ALLOWED_IMAGE:
            raise ProviderNotAllowed(f"image provider is not allowed: {name}")
        if name == "mock":
            if self.environment.lower() in {"prod", "production"}:
                raise ProviderNotAllowed("mock image provider is not available in production")
            return MockAIImageProvider()
        return ReplicateImageProvider()

    def select_tts_provider(self) -> str:
        return "edge"

    def video_capabilities(self) -> ProviderCapabilities | None:
        if not self.video_enabled:
            return None
        try:
            return self.select_video_provider().capabilities()
        except Exception:
            return None

    def image_capabilities(self) -> ProviderCapabilities | None:
        try:
            return self.select_image_provider().capabilities()
        except Exception:
            return None
