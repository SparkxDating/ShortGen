"""Atomic Redis rate limiter for multi-instance API deployments."""

from __future__ import annotations

import time


class RedisRateLimiter:
    def __init__(self, redis_url: str, limit: int, window_seconds: int = 60) -> None:
        import redis

        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def allow(self, key: str) -> bool:
        bucket = f"saas:ratelimit:{key}:{int(time.time() // self.window_seconds)}"
        count = self._client.incr(bucket)
        if count == 1:
            self._client.expire(bucket, self.window_seconds + 1)
        return int(count) <= self.limit
