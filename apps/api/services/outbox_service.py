"""Transactional outbox so Redis never sees a job before Postgres commits."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.models.outbox import JobOutbox
from apps.api.observability import log_event
from shared.queue.interface import JobQueue

logger = logging.getLogger("saas.outbox")


def enqueue_pending(db: Session, job_id: str, payload: dict) -> JobOutbox:
    existing = db.scalar(select(JobOutbox).where(JobOutbox.job_id == job_id))
    if existing:
        return existing
    row = JobOutbox(job_id=job_id, payload=payload, status="pending")
    db.add(row)
    db.flush()
    return row


def dispatch(db: Session, queue: JobQueue, job_id: str | None = None) -> int:
    query = select(JobOutbox).where(JobOutbox.status == "pending")
    if job_id:
        query = query.where(JobOutbox.job_id == job_id)
    rows = list(db.scalars(query.order_by(JobOutbox.created_at.asc())).all())
    sent = 0
    for row in rows:
        try:
            queue.enqueue_job(row.job_id, row.payload or {})
            row.status = "sent"
            row.sent_at = datetime.now(timezone.utc)
            row.attempts += 1
            sent += 1
            log_event(logger, "outbox_sent", job_id=row.job_id)
        except Exception as exc:
            row.attempts += 1
            row.last_error = str(exc)[:500]
            logger.warning("outbox dispatch failed job_id=%s", row.job_id)
    db.commit()
    return sent
