"""Queue contract used by the API and the worker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class QueueJob:
    job_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "QUEUED"
    cancelled: bool = False


class JobQueue(Protocol):
    def enqueue_job(self, job_id: str, payload: dict[str, Any] | None = None) -> QueueJob:
        """Place a job on the queue."""

    def dequeue_job(self, timeout_seconds: float = 5.0) -> QueueJob | None:
        """Block until a job is available or the timeout elapses."""

    def get_job_status(self, job_id: str) -> QueueJob | None:
        """Return queue-side metadata for a job."""

    def cancel_job(self, job_id: str) -> bool:
        """Mark a job cancelled. Returns False if the job is unknown."""

    def retry_job(self, job_id: str, payload: dict[str, Any] | None = None) -> QueueJob:
        """Re-queue an existing job."""

    def is_cancelled(self, job_id: str) -> bool:
        """True when a worker should stop between stages."""

    def set_job_status(self, job_id: str, status: str) -> None:
        """Update queue-side status (does not replace the database)."""
