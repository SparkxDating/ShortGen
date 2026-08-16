from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.models.job import Job, JobStatus
from apps.api.models.video import Video, VideoStatus
from apps.api.models.workspace import WorkspaceRole
from apps.api.services import credit_service, workspace_service
from apps.api.services.errors import NotFoundError, ServiceError
from shared.queue.interface import JobQueue
from video_engine.stages import stage_progress


def get_job(db: Session, job_id: str, user_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise NotFoundError("job not found")
    workspace_service.require_membership(db, job.workspace_id, user_id)
    return job


def cancel_job(db: Session, queue: JobQueue, job_id: str, user_id: str) -> Job:
    job = get_job(db, job_id, user_id)
    workspace_service.require_membership(db, job.workspace_id, user_id, WorkspaceRole.editor)
    if job.status in {JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
        raise ServiceError(f"job is already {job.status.lower()}", status_code=409)
    queue.cancel_job(job.id)
    job.status = JobStatus.CANCELLED.value
    job.current_stage = "CANCELLED"
    job.completed_at = datetime.now(timezone.utc)
    video = db.get(Video, job.video_id)
    if video and video.status not in {VideoStatus.completed.value}:
        video.status = VideoStatus.cancelled.value
    credit_service.refund(
        db,
        job.workspace_id,
        job.id,
        "Job cancelled",
        retry_count=job.retry_count or 0,
    )
    db.commit()
    db.refresh(job)
    return job


def retry_job(db: Session, queue: JobQueue, job_id: str, user_id: str) -> Job:
    job = get_job(db, job_id, user_id)
    workspace_service.require_membership(db, job.workspace_id, user_id, WorkspaceRole.editor)
    if job.status not in {JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
        raise ServiceError("only failed or cancelled jobs can be retried", status_code=409)
    next_retry = (job.retry_count or 0) + 1
    credit_service.reserve(
        db,
        job.workspace_id,
        job.id,
        credit_service.job_credit_cost(job),
        created_by=user_id,
        retry_count=next_retry,
    )
    job.status = JobStatus.QUEUED.value
    job.current_stage = "QUEUED"
    job.progress = stage_progress("QUEUED")
    job.error_message = None
    job.output_data = None
    job.retry_count = (job.retry_count or 0) + 1
    job.started_at = None
    job.completed_at = None
    video = db.get(Video, job.video_id)
    if video:
        video.status = VideoStatus.queued.value
        video.progress = 0
    queue.retry_job(job.id, job.input_data or {})
    db.commit()
    db.refresh(job)
    return job


def latest_job_for_video(db: Session, video_id: str) -> Job | None:
    return db.scalar(select(Job).where(Job.video_id == video_id).order_by(Job.created_at.desc()).limit(1))
