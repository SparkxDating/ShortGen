"""Build a queue implementation from configuration."""

from __future__ import annotations

from shared.queue.interface import JobQueue
from shared.queue.memory import InMemoryJobQueue


def create_job_queue(redis_url: str | None = None, *, force_memory: bool = False) -> JobQueue:
    if force_memory or not redis_url or redis_url.startswith("memory://"):
        return InMemoryJobQueue()
    from shared.queue.redis_queue import RedisJobQueue

    return RedisJobQueue(redis_url)
