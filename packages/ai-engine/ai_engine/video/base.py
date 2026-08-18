"""AI video provider interface. The Director never imports a concrete vendor."""

from __future__ import annotations

from typing import Protocol

from ai_engine.types import GenerationHandle, ProviderCapabilities


class AIVideoProvider(Protocol):
    name: str

    def capabilities(self) -> ProviderCapabilities: ...

    def create_generation(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        duration: float,
        model: str | None = None,
        negative_prompt: str | None = None,
        webhook_url: str | None = None,
    ) -> GenerationHandle: ...

    def get_generation_status(self, provider_job_id: str) -> GenerationHandle: ...

    def download_result(self, provider_job_id: str, destination: str) -> str: ...

    def cancel_generation(self, provider_job_id: str) -> GenerationHandle: ...
