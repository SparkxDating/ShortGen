from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.models.asset import Asset
from apps.api.models.job import Job, JobStatus, JobType
from apps.api.models.project import Project
from apps.api.models.template import Template
from apps.api.models.video import Video, VideoStatus
from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.job import JobResponse
from apps.api.schemas.video import VideoCreate, VideoResponse
from apps.api.models.outbox import IdempotencyKey
from apps.api.observability import log_event
from ai_engine.costs import credits_for_visual
from ai_engine.director.schema import VideoPlan
from apps.api.config import get_settings
from apps.api.services import credit_service, outbox_service, workspace_service
from apps.api.services.director_service import persist_plan
from apps.api.services.errors import NotFoundError, ServiceError
from apps.api.services.job_service import latest_job_for_video
from shared.queue.interface import JobQueue
import logging

logger = logging.getLogger("saas.videos")
from video_engine.stages import stage_progress


def _to_response(video: Video, job: Job | None = None) -> VideoResponse:
    payload = VideoResponse.model_validate(video)
    if job is not None:
        payload.latest_job = JobResponse.model_validate(job)
    return payload


def list_videos(
    db: Session,
    user_id: str,
    workspace_id: str | None = None,
    project_id: str | None = None,
) -> list[VideoResponse]:
    query = select(Video)
    if project_id:
        project = db.get(Project, project_id)
        if project is None:
            raise NotFoundError("project not found")
        workspace_service.require_membership(db, project.workspace_id, user_id)
        query = query.where(Video.project_id == project_id)
    elif workspace_id:
        workspace_service.require_membership(db, workspace_id, user_id)
        query = query.where(Video.workspace_id == workspace_id)
    else:
        memberships = workspace_service.list_workspaces(db, user_id)
        ids = [workspace.id for workspace, _ in memberships]
        if not ids:
            return []
        query = query.where(Video.workspace_id.in_(ids))
    videos = list(db.scalars(query.order_by(Video.created_at.desc())).all())
    return [_to_response(video, latest_job_for_video(db, video.id)) for video in videos]


def get_video(db: Session, video_id: str, user_id: str) -> VideoResponse:
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("video not found")
    workspace_service.require_membership(db, video.workspace_id, user_id)
    return _to_response(video, latest_job_for_video(db, video.id))


def create_video(
    db: Session,
    queue: JobQueue,
    user_id: str,
    payload: VideoCreate,
    idempotency_key: str | None = None,
) -> VideoResponse:
    project = db.get(Project, payload.project_id)
    if project is None or project.workspace_id != payload.workspace_id:
        raise NotFoundError("project not found")
    workspace_service.require_membership(db, payload.workspace_id, user_id, WorkspaceRole.editor)

    if idempotency_key:
        existing = db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.workspace_id == payload.workspace_id,
                IdempotencyKey.key == idempotency_key.strip(),
            )
        )
        if existing:
            return get_video(db, existing.video_id, user_id)

    if payload.template_id:
        template = db.get(Template, payload.template_id)
        if template is None or (
            template.workspace_id and template.workspace_id != payload.workspace_id
        ):
            raise NotFoundError("template not found")
        if template.workspace_id:
            workspace_service.require_membership(db, template.workspace_id, user_id)

    asset_ids = list(payload.asset_ids or [])
    if asset_ids:
        for asset_id in asset_ids:
            asset = db.get(Asset, asset_id)
            if asset is None or asset.workspace_id != payload.workspace_id:
                raise NotFoundError("asset not found")
    if payload.visual_source == "local" and not asset_ids:
        raise ServiceError("local media requires at least one workspace asset", status_code=400)
    settings = get_settings()
    if payload.visual_mode == "ai_video" and not settings.ai_video_enabled:
        raise ServiceError("AI video generation is temporarily unavailable", status_code=409)

    video = Video(
        workspace_id=payload.workspace_id,
        project_id=payload.project_id,
        title=payload.title.strip(),
        status=VideoStatus.queued.value,
        progress=stage_progress("QUEUED"),
        duration=float(payload.duration),
        aspect_ratio=payload.aspect_ratio,
        resolution=payload.resolution,
        created_by=user_id,
        visual_mode=payload.visual_mode,
        plan_json=payload.director_plan,
    )
    db.add(video)
    db.flush()

    input_data = {
        "topic": payload.topic,
        "title": payload.title,
        "video_language": payload.video_language,
        "duration": payload.duration,
        "aspect_ratio": payload.aspect_ratio,
        "resolution": payload.resolution,
        "voice": payload.voice,
        "visual_source": payload.visual_source,
        "video_script": payload.video_script,
        "subtitle_enabled": payload.subtitle_enabled,
        "video_clip_duration": payload.video_clip_duration,
        "match_materials_to_script": payload.match_materials_to_script,
        "video_concat_mode": payload.video_concat_mode,
        "asset_ids": asset_ids,
        "template_id": payload.template_id,
        "video_id": video.id,
        "workspace_id": payload.workspace_id,
        "project_id": payload.project_id,
        "visual_mode": payload.visual_mode,
        "style": payload.style,
        "tone": payload.tone,
        "target_platform": payload.target_platform,
        "director_plan": payload.director_plan,
        "credit_cost": _credit_cost(payload),
    }
    job = Job(
        workspace_id=payload.workspace_id,
        video_id=video.id,
        job_type=JobType.generate_video.value,
        status=JobStatus.QUEUED.value,
        progress=stage_progress("QUEUED"),
        current_stage="QUEUED",
        input_data=input_data,
    )
    db.add(job)
    db.flush()
    if payload.director_plan:
        try:
            persist_plan(db, video, VideoPlan.model_validate(payload.director_plan))
        except Exception:
            logger.warning("director plan not persisted video_id=%s", video.id)
    try:
        credit_service.reserve(
            db,
            payload.workspace_id,
            job.id,
            int(input_data["credit_cost"]),
            created_by=user_id,
            retry_count=0,
        )
    except Exception:
        db.rollback()
        raise
    outbox_service.enqueue_pending(db, job.id, input_data)
    if idempotency_key:
        db.add(
            IdempotencyKey(
                user_id=user_id,
                workspace_id=payload.workspace_id,
                key=idempotency_key.strip()[:120],
                video_id=video.id,
            )
        )
    db.commit()
    try:
        outbox_service.dispatch(db, queue, job.id)
    except Exception:
        logger.warning("queue dispatch deferred job_id=%s", job.id)
    db.refresh(video)
    db.refresh(job)
    log_event(
        logger,
        "job_created",
        job_id=job.id,
        workspace_id=payload.workspace_id,
        video_id=video.id,
    )
    return _to_response(video, job)


def delete_video(db: Session, video_id: str, user_id: str) -> None:
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("video not found")
    workspace_service.require_membership(db, video.workspace_id, user_id, WorkspaceRole.admin)
    db.delete(video)
    db.commit()


def _credit_cost(payload: VideoCreate) -> int:
    base = credit_service.estimate_credits(payload.duration, payload.resolution)
    extra = 0
    plan = payload.director_plan or {}
    scenes = plan.get("scenes") if isinstance(plan, dict) else None
    if scenes:
        extra = sum(credits_for_visual(str(scene.get("visual_type") or "")) for scene in scenes if isinstance(scene, dict))
    elif payload.visual_mode == "ai_video":
        extra = credits_for_visual("ai_video")
    elif payload.visual_mode in {"auto", "mixed"}:
        extra = credits_for_visual("ai_video")
    return base + extra


def start_generation(db: Session, queue: JobQueue, video_id: str, user_id: str) -> VideoResponse:
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("video not found")
    workspace_service.require_membership(db, video.workspace_id, user_id, WorkspaceRole.editor)
    if video.status in {VideoStatus.queued.value, VideoStatus.processing.value}:
        return get_video(db, video.id, user_id)
    settings = get_settings()
    if video.visual_mode == "ai_video" and not settings.ai_video_enabled:
        raise ServiceError("AI video generation is temporarily unavailable", status_code=409)
    cost = credit_service.estimate_credits(video.duration, video.resolution)
    if isinstance(video.plan_json, dict):
        for scene in video.plan_json.get("scenes") or []:
            if isinstance(scene, dict):
                cost += credits_for_visual(str(scene.get("visual_type") or ""))
    video.status = VideoStatus.queued.value
    job = Job(
        workspace_id=video.workspace_id,
        video_id=video.id,
        job_type=JobType.generate_video.value,
        status=JobStatus.QUEUED.value,
        current_stage="QUEUED",
        input_data={
            "topic": video.title,
            "title": video.title,
            "duration": int(video.duration or 30),
            "aspect_ratio": video.aspect_ratio,
            "resolution": video.resolution,
            "visual_mode": video.visual_mode,
            "director_plan": video.plan_json,
            "workspace_id": video.workspace_id,
            "video_id": video.id,
            "credit_cost": cost,
        },
    )
    db.add(job)
    db.flush()
    credit_service.reserve(db, video.workspace_id, job.id, cost, created_by=user_id)
    outbox_service.enqueue_pending(db, job.id, job.input_data or {})
    db.commit()
    try:
        outbox_service.dispatch(db, queue, job.id)
    except Exception:
        logger.warning("queue dispatch deferred job_id=%s", job.id)
    return get_video(db, video.id, user_id)


def enqueue_render(db: Session, queue: JobQueue, video: Video, user_id: str | None = None) -> Job:
    """Re-render from stored scene clips. Does not charge AI scene costs again."""
    cost = credit_service.estimate_credits(video.duration, video.resolution)
    job = Job(
        workspace_id=video.workspace_id,
        video_id=video.id,
        job_type=JobType.render_video.value,
        status=JobStatus.QUEUED.value,
        current_stage="QUEUED",
        input_data={
            "topic": video.title,
            "title": video.title,
            "duration": int(video.duration or 30),
            "aspect_ratio": video.aspect_ratio,
            "resolution": video.resolution,
            "visual_mode": video.visual_mode or "auto",
            "director_plan": video.plan_json,
            "workspace_id": video.workspace_id,
            "video_id": video.id,
            "credit_cost": cost,
            "reuse_ready_scenes": True,
        },
    )
    db.add(job)
    db.flush()
    credit_service.reserve(db, video.workspace_id, job.id, cost, created_by=user_id)
    video.status = VideoStatus.queued.value
    outbox_service.enqueue_pending(db, job.id, job.input_data or {})
    try:
        outbox_service.dispatch(db, queue, job.id)
    except Exception:
        logger.warning("render dispatch deferred job_id=%s", job.id)
    return job


def generation_status(db: Session, video_id: str, user_id: str) -> dict:
    video = get_video(db, video_id, user_id)
    from apps.api.models.scene import VideoScene

    scenes = list(db.scalars(select(VideoScene).where(VideoScene.video_id == video_id).order_by(VideoScene.order.asc())).all())
    return {
        "video_id": video.id,
        "status": video.status,
        "progress": video.progress,
        "visual_mode": video.visual_mode,
        "latest_job": video.latest_job.model_dump() if video.latest_job else None,
        "scenes": [
            {
                "id": scene.id,
                "order": scene.order,
                "status": scene.status,
                "progress": scene.progress,
                "visual_type": scene.visual_type,
            }
            for scene in scenes
        ],
    }
