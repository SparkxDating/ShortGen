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
from apps.api.services import credit_service, outbox_service, workspace_service
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
        "asset_ids": asset_ids,
        "template_id": payload.template_id,
        "video_id": video.id,
        "workspace_id": payload.workspace_id,
        "project_id": payload.project_id,
        "credit_cost": credit_service.estimate_credits(payload.duration, payload.resolution),
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
