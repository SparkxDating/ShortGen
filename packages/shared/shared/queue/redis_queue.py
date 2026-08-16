"""Redis-backed job queue. Redis is an implementation detail, not a business dependency."""

from __future__ import annotations

import json
from typing import Any

from shared.queue.interface import QueueJob

QUEUE_KEY = "saas:jobs:queue"
JOB_KEY_PREFIX = "saas:jobs:"
CANCEL_KEY_PREFIX = "saas:jobs:cancel:"


class RedisJobQueue:
    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def _job_key(self, job_id: str) -> str:
        return f"{JOB_KEY_PREFIX}{job_id}"

    def _cancel_key(self, job_id: str) -> str:
        return f"{CANCEL_KEY_PREFIX}{job_id}"

    def enqueue_job(self, job_id: str, payload: dict[str, Any] | None = None) -> QueueJob:
        job = QueueJob(job_id=job_id, payload=payload or {}, status="QUEUED", cancelled=False)
        self._client.hset(
            self._job_key(job_id),
            mapping={
                "job_id": job_id,
                "payload": json.dumps(job.payload),
                "status": "QUEUED",
                "cancelled": "0",
            },
        )
        self._client.delete(self._cancel_key(job_id))
        self._client.lpush(QUEUE_KEY, job_id)
        return job

    def dequeue_job(self, timeout_seconds: float = 5.0) -> QueueJob | None:
        result = self._client.brpop(QUEUE_KEY, timeout=max(1, int(timeout_seconds)))
        if not result:
            return None
        _, job_id = result
        if self.is_cancelled(job_id):
            self.set_job_status(job_id, "CANCELLED")
            return None
        self.set_job_status(job_id, "RUNNING")
        return self.get_job_status(job_id)

    def get_job_status(self, job_id: str) -> QueueJob | None:
        data = self._client.hgetall(self._job_key(job_id))
        if not data:
            return None
        payload_raw = data.get("payload") or "{}"
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            payload = {}
        return QueueJob(
            job_id=data.get("job_id", job_id),
            payload=payload if isinstance(payload, dict) else {},
            status=data.get("status", "QUEUED"),
            cancelled=data.get("cancelled") == "1" or self.is_cancelled(job_id),
        )

    def cancel_job(self, job_id: str) -> bool:
        if not self._client.exists(self._job_key(job_id)):
            return False
        self._client.set(self._cancel_key(job_id), "1")
        self._client.hset(self._job_key(job_id), mapping={"cancelled": "1", "status": "CANCELLED"})
        return True

    def retry_job(self, job_id: str, payload: dict[str, Any] | None = None) -> QueueJob:
        existing = self.get_job_status(job_id)
        next_payload = payload if payload is not None else (existing.payload if existing else {})
        return self.enqueue_job(job_id, next_payload)

    def is_cancelled(self, job_id: str) -> bool:
        return bool(self._client.exists(self._cancel_key(job_id)))

    def set_job_status(self, job_id: str, status: str) -> None:
        self._client.hset(self._job_key(job_id), "status", status)
