"""In-process queue used for tests and local runs without Redis."""

from __future__ import annotations

import queue
import threading
from typing import Any

from shared.queue.interface import QueueJob


class InMemoryJobQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._jobs: dict[str, QueueJob] = {}
        self._lock = threading.RLock()

    def enqueue_job(self, job_id: str, payload: dict[str, Any] | None = None) -> QueueJob:
        with self._lock:
            job = QueueJob(job_id=job_id, payload=payload or {}, status="QUEUED", cancelled=False)
            self._jobs[job_id] = job
            self._queue.put(job_id)
            return job

    def dequeue_job(self, timeout_seconds: float = 5.0) -> QueueJob | None:
        try:
            job_id = self._queue.get(timeout=timeout_seconds)
        except queue.Empty:
            return None
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.cancelled:
                return None
            job.status = "RUNNING"
            return job

    def get_job_status(self, job_id: str) -> QueueJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return QueueJob(
                job_id=job.job_id,
                payload=dict(job.payload),
                status=job.status,
                cancelled=job.cancelled,
            )

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            job.cancelled = True
            job.status = "CANCELLED"
            return True

    def retry_job(self, job_id: str, payload: dict[str, Any] | None = None) -> QueueJob:
        with self._lock:
            existing = self._jobs.get(job_id)
            next_payload = payload if payload is not None else (existing.payload if existing else {})
            job = QueueJob(job_id=job_id, payload=dict(next_payload), status="QUEUED", cancelled=False)
            self._jobs[job_id] = job
            self._queue.put(job_id)
            return job

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.cancelled)

    def set_job_status(self, job_id: str, status: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                job = QueueJob(job_id=job_id, status=status)
                self._jobs[job_id] = job
            else:
                job.status = status
