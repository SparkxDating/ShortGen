from __future__ import annotations

from pathlib import Path

from ai_engine.types import GenerationHandle, GenerationStatus, ProviderCapabilities


class MockAIImageProvider:
    name = "mock"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self._jobs: dict[str, GenerationHandle] = {}

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name,
            models=["mock-image"],
            aspect_ratios=["9:16", "16:9", "1:1"],
            durations=[0],
            production=False,
        )

    def generate_image(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        model: str | None = None,
        negative_prompt: str | None = None,
    ) -> GenerationHandle:
        job_id = f"mock-image-{abs(hash(prompt)) % 10_000_000}"
        handle = GenerationHandle(
            provider=self.name,
            provider_job_id=job_id,
            status=GenerationStatus.FAILED if self.fail else GenerationStatus.COMPLETED,
            progress=100,
            result_url=None if self.fail else f"mock://{job_id}",
            error="mock image forced failure" if self.fail else None,
        )
        self._jobs[job_id] = handle
        return handle

    def get_generation_status(self, provider_job_id: str) -> GenerationHandle:
        return self._jobs.get(
            provider_job_id,
            GenerationHandle(provider=self.name, provider_job_id=provider_job_id, status=GenerationStatus.FAILED),
        )

    def download_result(self, provider_job_id: str, destination: str) -> str:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 1x1 PNG
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00"
            b"\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return str(path)
