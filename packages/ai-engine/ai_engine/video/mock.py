"""Deterministic development/CI provider. Never listed as production."""

from __future__ import annotations

from pathlib import Path

from ai_engine.types import GenerationHandle, GenerationStatus, ProviderCapabilities


class MockAIVideoProvider:
    name = "mock"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self._jobs: dict[str, GenerationHandle] = {}

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name,
            models=["mock-video"],
            aspect_ratios=["9:16", "16:9", "1:1"],
            durations=[5, 10],
            supports_negative_prompt=True,
            production=False,
        )

    def create_generation(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        duration: float,
        model: str | None = None,
        negative_prompt: str | None = None,
        webhook_url: str | None = None,
    ) -> GenerationHandle:
        job_id = f"mock-video-{abs(hash((prompt, aspect_ratio, duration))) % 10_000_000}"
        status = GenerationStatus.FAILED if self.fail else GenerationStatus.COMPLETED
        handle = GenerationHandle(
            provider=self.name,
            provider_job_id=job_id,
            status=status,
            progress=100 if not self.fail else 40,
            result_url=None if self.fail else f"mock://{job_id}",
            error="mock provider forced failure" if self.fail else None,
            raw={"prompt": prompt, "aspect_ratio": aspect_ratio, "duration": duration, "model": model},
        )
        self._jobs[job_id] = handle
        return handle

    def get_generation_status(self, provider_job_id: str) -> GenerationHandle:
        return self._jobs.get(
            provider_job_id,
            GenerationHandle(
                provider=self.name,
                provider_job_id=provider_job_id,
                status=GenerationStatus.FAILED,
                error="unknown mock job",
            ),
        )

    def download_result(self, provider_job_id: str, destination: str) -> str:
        handle = self.get_generation_status(provider_job_id)
        if handle.status != GenerationStatus.COMPLETED:
            raise RuntimeError(handle.error or "mock video is not ready")
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_tiny_mp4(path)
        return str(path)

    def cancel_generation(self, provider_job_id: str) -> GenerationHandle:
        handle = self.get_generation_status(provider_job_id)
        handle.status = GenerationStatus.CANCELLED
        self._jobs[provider_job_id] = handle
        return handle


def _write_tiny_mp4(path: Path) -> None:
    try:
        from moviepy import ColorClip

        clip = ColorClip(size=(64, 64), color=(20, 40, 80)).with_duration(1).with_fps(8)
        clip.write_videofile(str(path), fps=8, audio=False, logger=None, threads=1)
        clip.close()
        if path.is_file() and path.stat().st_size > 0:
            return
    except Exception:
        pass
    path.write_bytes(b"\x00\x00\x00\x1cftypmp42" + b"\x00" * 64)
