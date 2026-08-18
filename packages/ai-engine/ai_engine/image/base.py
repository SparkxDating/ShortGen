from __future__ import annotations

from typing import Protocol

from ai_engine.types import GenerationHandle, ProviderCapabilities


class AIImageProvider(Protocol):
    name: str

    def capabilities(self) -> ProviderCapabilities: ...

    def generate_image(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        model: str | None = None,
        negative_prompt: str | None = None,
    ) -> GenerationHandle: ...

    def get_generation_status(self, provider_job_id: str) -> GenerationHandle: ...

    def download_result(self, provider_job_id: str, destination: str) -> str: ...
