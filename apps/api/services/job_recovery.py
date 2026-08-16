"""Detect stale RUNNING jobs and recover them."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.models.job import Job, JobStatus
from apps.api.models.video import Video, VideoStatus
from apps.api.observability import log_event
from apps.api.services import credit_service, outbox_service
from shared.queue.interface import JobQueue

logger = logging.getLogger("saas.recovery")


def recover_stale_jobs(db: Session, queue: JobQueue) -> int:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max(30, settings.job_stale_seconds))
    jobs = list(
        db.scalars(
            select(Job).where(
                Job.status == JobStatus.RUNNING.value,
                or_(Job.heartbeat_at.is_(None), Job.heartbeat_at < cutoff),
            )
        ).all()
    )
    recovered = 0
    for job in jobs:
        job.current_stage = "STALE"
        if (job.retry_count or 0) < settings.job_max_retries:
            credit_service.refund(db, job.workspace_id, job.id, "Stale worker lease", retry_count=job.retry_count or 0)
            next_retry = (job.retry_count or 0) + 1
            credit_service.reserve(
                db,
                job.workspace_id,
                job.id,
                credit_service.job_credit_cost(job),
                retry_count=next_retry,
            )
            job.retry_count = next_retry
            job.status = JobStatus.QUEUED.value
            job.current_stage = "QUEUED"
            job.worker_id = None
            job.started_at = None
            job.heartbeat_at = None
            outbox_service.enqueue_pending(db, job.id, job.input_data or {})
            recovered += 1
            log_event(logger, "job_stale_requeued", job_id=job.id, workspace_id=job.workspace_id)
        else:
            credit_service.refund(
                db, job.workspace_id, job.id, "Stale job exceeded retries", retry_count=job.retry_count or 0
            )
            job.status = JobStatus.FAILED.value
            job.current_stage = "FAILED"
            job.error_message = "worker lease expired"
            job.completed_at = datetime.now(timezone.utc)
            video = db.get(Video, job.video_id)
            if video and video.status != VideoStatus.completed.value:
                video.status = VideoStatus.failed.value
            log_event(logger, "job_stale_failed", job_id=job.id, workspace_id=job.workspace_id)
            recovered += 1
    if jobs:
        db.commit()
        try:
            outbox_service.dispatch(db, queue)
        except Exception:
            logger.warning("stale job requeue dispatch deferred")
    return recovered
