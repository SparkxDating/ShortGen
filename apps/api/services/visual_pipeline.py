"""Per-scene visual generation. Director never calls a vendor from here either."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

from ai_engine.costs import credits_for_visual
from ai_engine.poll import poll_until
from ai_engine.prompts import DEFAULT_NEGATIVE
from ai_engine.router import AIProviderRouter, ProviderNotAllowed
from ai_engine.types import GenerationHandle, GenerationStatus
from apps.api.config import get_settings
from apps.api.models.asset import Asset
from apps.api.models.scene import ProviderGeneration, VideoScene
from apps.api.models.video import Video
from sqlalchemy.orm import Session

logger = logging.getLogger("saas.visuals")


def fallback_chain(visual_mode: str) -> list[str]:
    mode = (visual_mode or "auto").lower()
    if mode == "ai_video":
        return []
    raw = (get_settings().ai_video_fallback_policy or "ai_image,stock").split(",")
    return [item.strip() for item in raw if item.strip() in {"ai_image", "stock"}]


def generate_scene_visual(
    db: Session,
    *,
    video: Video,
    scene: VideoScene,
    work_dir: Path,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    settings = get_settings()
    router = AIProviderRouter(
        environment=settings.environment,
        video_provider=settings.ai_video_provider,
        image_provider=settings.ai_image_provider,
        video_enabled=settings.ai_video_enabled,
    )
    wanted = scene.visual_type
    attempts = [wanted]
    if wanted == "ai_video":
        attempts.extend(fallback_chain(video.visual_mode))
    elif wanted == "ai_image":
        if video.visual_mode != "ai_video":
            attempts.append("stock")
    last_error = "visual generation failed"
    for kind in attempts:
        try:
            path = _generate_kind(
                db,
                video=video,
                scene=scene,
                kind=kind,
                work_dir=work_dir,
                router=router,
                should_cancel=should_cancel,
            )
            scene.visual_type = kind
            scene.status = "ready"
            scene.progress = 100
            scene.error_message = None if kind == wanted else f"fell back to {kind}"
            store_scene_clip(db, video, scene, path)
            db.commit()
            return path
        except Exception as exc:
            last_error = str(exc) or last_error
            logger.warning(
                "scene_visual_failed video_id=%s scene_id=%s kind=%s error=%s",
                video.id,
                scene.id,
                kind,
                last_error,
            )
            continue
    scene.status = "failed"
    scene.error_message = last_error
    db.commit()
    raise RuntimeError(last_error)


def store_scene_clip(db: Session, video: Video, scene: VideoScene, path: Path) -> None:
    from apps.api.api.deps import get_storage
    from apps.api.models.asset import Asset

    suffix = path.suffix.lower() or ".mp4"
    key = f"workspaces/{video.workspace_id}/videos/{video.id}/scenes/{scene.id}{suffix}"
    storage = get_storage()
    stored = storage.upload_file(str(path), key, "video/mp4" if suffix == ".mp4" else "application/octet-stream")
    public = storage.get_public_url(stored)
    asset = Asset(
        workspace_id=video.workspace_id,
        name=f"scene-{scene.order}",
        kind="video",
        object_key=stored,
        public_url=public,
        content_type="video/mp4",
        size_bytes=path.stat().st_size if path.is_file() else 0,
        original_filename=path.name,
        created_by=video.created_by,
    )
    db.add(asset)
    db.flush()
    scene.asset_id = asset.id


def load_scene_clip(db: Session, video: Video, scene: VideoScene, dest: Path) -> Path | None:
    if scene.status != "ready" or not scene.asset_id:
        return None
    asset = db.get(Asset, scene.asset_id)
    if asset is None or asset.workspace_id != video.workspace_id:
        return None
    from apps.api.api.deps import get_storage

    dest.parent.mkdir(parents=True, exist_ok=True)
    target = dest.with_suffix(Path(asset.original_filename).suffix or ".mp4")
    get_storage().download_file(asset.object_key, str(target))
    return target


def _generate_kind(
    db: Session,
    *,
    video: Video,
    scene: VideoScene,
    kind: str,
    work_dir: Path,
    router: AIProviderRouter,
    should_cancel: Callable[[], bool] | None,
) -> Path:
    dest = work_dir / f"{scene.id}-{kind}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if kind == "user_asset":
        return _from_user_asset(db, video, scene, dest.with_suffix(".bin"))
    if kind == "stock":
        return _from_stock(scene, dest)
    if kind == "ai_image":
        provider = router.select_image_provider(scene.provider or None)
        handle = provider.generate_image(
            prompt=scene.visual_prompt or scene.narration,
            aspect_ratio=video.aspect_ratio,
            negative_prompt=DEFAULT_NEGATIVE,
        )
        _record_generation(db, video, scene, handle, kind)
        handle = _wait(provider.get_generation_status, handle, should_cancel)
        image_path = dest.with_suffix(".png")
        provider.download_result(handle.provider_job_id, str(image_path))
        return _still_to_clip(image_path, dest.with_suffix(".mp4"), scene.duration)
    if kind == "ai_video":
        if not get_settings().ai_video_enabled:
            raise ProviderNotAllowed("AI video generation is temporarily unavailable")
        provider = router.select_video_provider(scene.provider or None)
        caps = provider.capabilities()
        if video.aspect_ratio not in caps.aspect_ratios:
            raise RuntimeError(f"provider does not support {video.aspect_ratio}")
        duration = _fit_duration(scene.duration, caps.durations)
        handle = provider.create_generation(
            prompt=scene.visual_prompt or scene.narration,
            aspect_ratio=video.aspect_ratio,
            duration=duration,
            model=get_settings().ai_video_model,
            negative_prompt=DEFAULT_NEGATIVE if caps.supports_negative_prompt else None,
        )
        _record_generation(db, video, scene, handle, kind)
        handle = _wait(provider.get_generation_status, handle, should_cancel)
        video_path = dest.with_suffix(".mp4")
        provider.download_result(handle.provider_job_id, str(video_path))
        scene.provider = provider.name
        scene.provider_job_id = handle.provider_job_id
        return video_path
    raise RuntimeError(f"unsupported visual type {kind}")


def _wait(fetch, handle: GenerationHandle, should_cancel) -> GenerationHandle:
    if handle.status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED, GenerationStatus.CANCELLED}:
        if handle.status != GenerationStatus.COMPLETED:
            raise RuntimeError(handle.error or handle.status.value)
        return handle

    def _fetch():
        return fetch(handle.provider_job_id)

    result = poll_until(
        _fetch,
        is_done=lambda item: item.status is GenerationStatus.COMPLETED,
        is_failed=lambda item: item.status in {GenerationStatus.FAILED, GenerationStatus.CANCELLED},
        should_cancel=should_cancel,
    )
    if result.status != GenerationStatus.COMPLETED:
        raise RuntimeError(result.error or result.status.value)
    return result


def _record_generation(db: Session, video: Video, scene: VideoScene, handle: GenerationHandle, kind: str) -> None:
    db.add(
        ProviderGeneration(
            workspace_id=video.workspace_id,
            video_id=video.id,
            scene_id=scene.id,
            provider=handle.provider,
            model=get_settings().ai_video_model if kind == "ai_video" else "",
            duration=scene.duration,
            provider_generation_id=handle.provider_job_id,
            status=handle.status.value,
            credits_reserved=credits_for_visual(kind),
        )
    )
    scene.provider = handle.provider
    scene.provider_job_id = handle.provider_job_id
    scene.status = "processing"
    db.commit()


def _from_user_asset(db: Session, video: Video, scene: VideoScene, dest: Path) -> Path:
    if not scene.asset_id:
        raise RuntimeError("user_asset scene is missing an asset")
    asset = db.get(Asset, scene.asset_id)
    if asset is None or asset.workspace_id != video.workspace_id:
        raise RuntimeError("asset is not in this workspace")
    from apps.api.api.deps import get_storage

    storage = get_storage()
    dest = dest.with_suffix(Path(asset.original_filename).suffix or ".mp4")
    storage.download_file(asset.object_key, str(dest))
    if dest.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        return _still_to_clip(dest, dest.with_suffix(".mp4"), scene.duration)
    return dest


def _from_stock(scene: VideoScene, dest: Path) -> Path:
    query = scene.visual_query or scene.narration
    try:
        from app.services.material import search_videos_pexels
        from app.models.schema import VideoAspect

        items = search_videos_pexels(query[:80], minimum_duration=2, video_aspect=VideoAspect.portrait)
        url = None
        if items:
            first = items[0]
            url = first.get("url") if isinstance(first, dict) else getattr(first, "url", None)
        if url:
            import requests

            dest = dest.with_suffix(".mp4")
            with requests.get(url, stream=True, timeout=120) as response:
                response.raise_for_status()
                dest.write_bytes(response.content)
            return dest
    except Exception as exc:
        logger.info("stock fetch skipped query=%s error=%s", query, exc)
    return _demo_clip(dest.with_suffix(".mp4"), scene.duration)


def _demo_clip(path: Path, duration: float) -> Path:
    from video_engine.generation_adapter import _demo_materials

    clips = _demo_materials(f"scene-{path.stem}", duration or 4)
    if clips:
        return Path(clips[0])
    from ai_engine.video.mock import MockAIVideoProvider

    MockAIVideoProvider().download_result("demo", str(path))
    return path


def _still_to_clip(image: Path, dest: Path, duration: float) -> Path:
    try:
        from moviepy import ImageClip

        clip = ImageClip(str(image)).with_duration(max(2.0, float(duration or 4))).with_fps(24)
        clip.write_videofile(str(dest), fps=24, audio=False, logger=None, threads=1)
        clip.close()
        return dest
    except Exception:
        return _demo_clip(dest, duration)


def _fit_duration(requested: float, allowed: list[int]) -> float:
    if not allowed:
        return requested
    return min(allowed, key=lambda item: abs(item - requested))
