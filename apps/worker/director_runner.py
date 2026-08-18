"""Orchestrate Director scenes, then hand clips to the existing renderer."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from ai_engine.director.planner import plan_video
from ai_engine.director.schema import VideoPlan
from apps.api.config import get_settings
from apps.api.models.job import Job
from apps.api.models.scene import VideoScene, VideoVersion
from apps.api.models.video import Video
from apps.api.services.director_service import persist_plan
from apps.api.services.visual_pipeline import generate_scene_visual, load_scene_clip
from sqlalchemy import select

logger = logging.getLogger("saas.director")
Progress = Callable[[str, int, dict[str, Any] | None], None]


def prepare_local_materials(
    db: Session,
    job: Job,
    video: Video,
    work_dir: Path,
    on_progress: Progress,
    should_cancel: Callable[[], bool],
) -> list[str]:
    plan = _ensure_plan(db, job, video)
    scenes = list(
        db.scalars(select(VideoScene).where(VideoScene.video_id == video.id).order_by(VideoScene.order.asc())).all()
    )
    if not scenes:
        persist_plan(db, video, plan)
        scenes = list(
            db.scalars(select(VideoScene).where(VideoScene.video_id == video.id).order_by(VideoScene.order.asc())).all()
        )
    on_progress("PLANNING", 18, {"scenes": len(scenes)})
    workers = max(1, min(get_settings().max_parallel_scene_generations, len(scenes)))
    paths: dict[str, str] = {}
    errors: list[str] = []

    def _one(scene: VideoScene) -> tuple[str, str]:
        reuse = load_scene_clip(db, video, scene, work_dir / f"{scene.id}-ready")
        if reuse and reuse.is_file():
            return scene.id, str(reuse)
        path = generate_scene_visual(db, video=video, scene=scene, work_dir=work_dir, should_cancel=should_cancel)
        return scene.id, str(path)

    completed = 0
    if workers == 1:
        for scene in scenes:
            if should_cancel():
                raise RuntimeError("generation cancelled")
            scene_id, path = _one(scene)
            paths[scene_id] = path
            completed += 1
            pct = 20 + int(40 * completed / max(1, len(scenes)))
            on_progress("FETCHING_MEDIA", pct, {"scene_id": scene_id})
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_one, scene): scene for scene in scenes}
            for future in as_completed(futures):
                scene = futures[future]
                try:
                    scene_id, path = future.result()
                    paths[scene_id] = path
                except Exception as exc:
                    errors.append(f"{scene.id}: {exc}")
                completed += 1
                pct = 20 + int(40 * completed / max(1, len(scenes)))
                on_progress("FETCHING_MEDIA", pct, {"done": completed})
    if errors and video.visual_mode == "ai_video":
        raise RuntimeError("AI video only: " + "; ".join(errors))
    ordered = [paths[scene.id] for scene in scenes if scene.id in paths]
    if not ordered:
        raise RuntimeError("; ".join(errors) or "no scene visuals were produced")
    script = " ".join(scene.narration for scene in scenes if scene.narration)
    job.input_data = {**(job.input_data or {}), "video_script": script, "visual_source": "local"}
    return ordered


def snapshot_version(db: Session, video: Video, render_url: str | None) -> None:
    existing = list(db.scalars(select(VideoVersion).where(VideoVersion.video_id == video.id)).all())
    number = 1 + max((item.version_number for item in existing), default=0)
    db.add(VideoVersion(video_id=video.id, version_number=number, render_url=render_url))


def _ensure_plan(db: Session, job: Job, video: Video) -> VideoPlan:
    payload = job.input_data or {}
    raw = payload.get("director_plan") or video.plan_json
    if isinstance(raw, dict):
        try:
            return VideoPlan.model_validate(raw)
        except Exception:
            raw = None
    topic = str(payload.get("topic") or video.title)
    script = str(payload.get("video_script") or "")
    return plan_video(
        topic=topic,
        script=script or topic,
        duration=int(payload.get("duration") or video.duration or 30),
        language=str(payload.get("video_language") or "en-US"),
        aspect_ratio=str(payload.get("aspect_ratio") or video.aspect_ratio),
        resolution=str(payload.get("resolution") or video.resolution),
        style=str(payload.get("style") or "cinematic"),
        tone=str(payload.get("tone") or "informative"),
        target_platform=str(payload.get("target_platform") or "short"),
        visual_mode=str(payload.get("visual_mode") or video.visual_mode or "auto"),
        raw_json=raw if isinstance(raw, str) else None,
        asset_ids=list(payload.get("asset_ids") or []),
    )
