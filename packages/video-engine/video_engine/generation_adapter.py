"""Adapter around the existing MoneyPrinterTurbo generation services.

This module does not reimplement LLM, TTS, Whisper, stock retrieval, or
MoviePy rendering. It calls ``app.services.task`` functions in the same
order as the original pipeline so progress can be reported to the SaaS
job table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from video_engine.stages import stage_progress

ProgressCallback = Callable[[str, int, dict[str, Any] | None], None]
CancelCheck = Callable[[], bool]


class GenerationError(RuntimeError):
    """Raised when an existing pipeline stage returns a failure."""


class GenerationCancelled(RuntimeError):
    """Raised when the worker observes a cancel request between stages."""


@dataclass
class GenerationResult:
    task_id: str
    script: str = ""
    terms: list[str] | str = field(default_factory=list)
    audio_file: str = ""
    audio_duration: float = 0
    subtitle_path: str = ""
    materials: list[str] = field(default_factory=list)
    video_paths: list[str] = field(default_factory=list)
    combined_video_paths: list[str] = field(default_factory=list)
    warnings: list[Any] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def primary_video_path(self) -> str | None:
        if self.video_paths:
            return self.video_paths[0]
        return None


def _demo_materials(task_id: str, audio_duration: float) -> list[str]:
    """Use bundled stills as local clips when stock APIs are not configured."""
    from app.utils import utils

    roots = [
        Path(utils.root_dir()) / "test" / "resources",
        Path(utils.root_dir()) / "resource",
    ]
    images: list[Path] = []
    for root in roots:
        if root.is_dir():
            images.extend(sorted(root.glob("*.png"))[:6])
    if not images:
        return []
    out_dir = Path(utils.task_dir(task_id))
    out_dir.mkdir(parents=True, exist_ok=True)
    clip_len = max(2.0, min(5.0, float(audio_duration or 8) / max(1, len(images)))
    )
    paths: list[str] = []
    try:
        from moviepy import ImageClip
    except Exception:
        return []
    for index, image in enumerate(images):
        dest = out_dir / f"demo-{index}.mp4"
        try:
            clip = ImageClip(str(image)).with_duration(clip_len).with_fps(24)
            clip.write_videofile(str(dest), fps=24, audio=False, logger=None, threads=1)
            clip.close()
            if dest.is_file():
                paths.append(str(dest))
        except Exception:
            continue
    return paths


def _local_terms(subject: str, script: str) -> list[str]:
    """Stock search terms when no LLM key is configured."""
    words = re.findall(r"[A-Za-z]{3,}", f"{subject} {script}")
    unique: list[str] = []
    for word in words:
        lower = word.lower()
        if lower not in unique:
            unique.append(lower)
    return unique[:5] or ["b-roll", "city", "nature"]


class MoneyPrinterTurboGenerationAdapter:
    """Thin façade over ``app.services.task``.

    The existing engine remains the source of truth. Do not add a second
    generation implementation here.
    """

    def _ensure_engine(self) -> None:
        # Imported lazily so API processes that never generate video do not
        # pull MoviePy/Whisper at import time.
        from app.models.schema import VideoParams  # noqa: F401
        from app.services import task as task_service  # noqa: F401
        try:
            from apps.api.services.provider_keys_service import reload_from_disk

            reload_from_disk()
        except Exception:
            pass

    def build_params(self, payload: dict[str, Any]):
        from app.models.schema import VideoAspect, VideoConcatMode, VideoParams

        aspect = payload.get("aspect_ratio") or payload.get("video_aspect") or "9:16"
        source = payload.get("visual_source") or payload.get("video_source") or "stock"
        if source in {"stock", "Stock Media", "pexels"}:
            video_source = payload.get("video_source") or "pexels"
        else:
            video_source = "local"

        subject = (
            payload.get("topic")
            or payload.get("video_subject")
            or payload.get("title")
            or ""
        )
        local_paths = [str(path) for path in (payload.get("local_material_paths") or []) if path]
        materials = None
        if local_paths:
            from app.models.schema import MaterialInfo

            video_source = "local"
            clip_duration = int(payload.get("video_clip_duration") or 5)
            materials = [
                MaterialInfo(provider="local", url=path, duration=clip_duration) for path in local_paths
            ]
        return VideoParams(
            video_subject=str(subject),
            video_script=str(payload.get("video_script") or ""),
            video_aspect=VideoAspect(aspect) if aspect in {item.value for item in VideoAspect} else VideoAspect.portrait,
            video_language=str(payload.get("video_language") or payload.get("language") or ""),
            voice_name=str(
                payload.get("voice") or payload.get("voice_name") or "en-US-JennyNeural-Female"
            ),
            video_source=video_source,
            video_materials=materials,
            video_concat_mode=(
                VideoConcatMode.sequential
                if payload.get("match_materials_to_script", True)
                or str(payload.get("video_concat_mode") or "sequential") == "sequential"
                else VideoConcatMode.random
            ),
            video_clip_duration=int(payload.get("video_clip_duration") or 3),
            match_materials_to_script=bool(payload.get("match_materials_to_script", True)),
            paragraph_number=int(payload.get("paragraph_number") or 1),
            subtitle_enabled=bool(payload.get("subtitle_enabled", True)),
        )

    def generate_script(self, task_id: str, params) -> str:
        from app.services.task import generate_script

        script = generate_script(task_id, params)
        if script and not (isinstance(script, str) and script.startswith("Error: ")):
            return script
        from apps.api.services.local_script import write_script

        return write_script(str(params.video_subject or ""), str(params.video_language or ""))

    def generate_voice(self, task_id: str, params, video_script: str):
        from app.services.task import generate_audio

        audio_file, audio_duration, sub_maker = generate_audio(task_id, params, video_script)
        if not audio_file:
            raise GenerationError("failed to prepare narration audio")
        return audio_file, audio_duration, sub_maker

    def generate_subtitles(self, task_id: str, params, video_script: str, sub_maker, audio_file: str) -> str:
        from app.services.task import generate_subtitle

        return generate_subtitle(task_id, params, video_script, sub_maker, audio_file) or ""

    def fetch_media(self, task_id: str, params, video_terms, audio_duration):
        from app.services.task import get_video_materials

        try:
            materials = get_video_materials(task_id, params, video_terms, audio_duration)
        except Exception as exc:
            raise GenerationError(f"failed to prepare video materials: {exc}") from exc
        if not materials:
            raise GenerationError("failed to prepare video materials")
        return materials

    def render_video(self, task_id: str, params, downloaded_videos, audio_file, subtitle_path, audio_duration):
        from app.services.task import generate_final_videos

        final_paths, combined_paths, warnings = generate_final_videos(
            task_id,
            params,
            downloaded_videos,
            audio_file,
            subtitle_path,
            audio_duration,
        )
        if not final_paths:
            raise GenerationError("failed to generate final video")
        return final_paths, combined_paths, warnings or []

    def create_video(
        self,
        payload: dict[str, Any],
        *,
        task_id: str | None = None,
        on_progress: ProgressCallback | None = None,
        should_cancel: CancelCheck | None = None,
    ) -> GenerationResult:
        """Run the existing pipeline with SaaS progress hooks.

        Stage order matches ``app.services.task._run_pipeline``.
        """
        self._ensure_engine()
        from app.services.task import generate_terms, save_script_data

        task_id = task_id or f"saas-{uuid4().hex}"
        params = self.build_params(payload)
        result = GenerationResult(task_id=task_id)

        def report(stage: str, extra: dict[str, Any] | None = None) -> None:
            if on_progress:
                on_progress(stage, stage_progress(stage), extra)

        def check_cancel() -> None:
            if should_cancel and should_cancel():
                raise GenerationCancelled("generation cancelled")

        report("ANALYZING")
        check_cancel()

        report("GENERATING_SCRIPT")
        script = self.generate_script(task_id, params)
        result.script = script
        check_cancel()

        report("PLANNING")
        terms: list[str] | str = []
        if getattr(params, "video_source", "pexels") != "local":
            try:
                terms = generate_terms(task_id, params, script)
            except Exception:
                terms = []
            if not terms:
                terms = _local_terms(str(getattr(params, "video_subject", "") or ""), script)
        result.terms = terms
        save_script_data(task_id, script, terms, params)
        check_cancel()

        # Audio before media so stock downloads can use the narration duration,
        # matching the original pipeline order.
        report("GENERATING_AUDIO")
        audio_file, audio_duration, sub_maker = self.generate_voice(task_id, params, script)
        result.audio_file = audio_file
        result.audio_duration = float(audio_duration or 0)
        check_cancel()

        report("GENERATING_SUBTITLES")
        subtitle_path = self.generate_subtitles(task_id, params, script, sub_maker, audio_file)
        result.subtitle_path = subtitle_path
        check_cancel()

        report("FETCHING_MEDIA")
        try:
            materials = self.fetch_media(task_id, params, terms, audio_duration)
        except GenerationError:
            materials = _demo_materials(task_id, float(audio_duration or 8))
            if not materials:
                raise
        result.materials = list(materials)
        check_cancel()

        report("RENDERING")
        video_paths, combined_paths, warnings = self.render_video(
            task_id,
            params,
            materials,
            audio_file,
            subtitle_path,
            audio_duration,
        )
        result.video_paths = list(video_paths)
        result.combined_video_paths = list(combined_paths)
        result.warnings = list(warnings)
        result.raw = {
            "script": script,
            "terms": terms,
            "audio_file": audio_file,
            "audio_duration": audio_duration,
            "subtitle_path": subtitle_path,
            "materials": materials,
            "videos": video_paths,
            "combined_videos": combined_paths,
            "warnings": warnings,
        }
        return result
