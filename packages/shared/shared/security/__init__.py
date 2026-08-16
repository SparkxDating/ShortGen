from shared.security.filenames import safe_filename, safe_object_key
from shared.security.rate_limit import RateLimiter

__all__ = ["safe_filename", "safe_object_key", "RateLimiter", "create_rate_limiter"]


def create_rate_limiter(backend: str, limit: int, redis_url: str = "", window_seconds: int = 60):
    if (backend or "memory").lower() == "redis" and redis_url and not redis_url.startswith("memory://"):
        from shared.security.redis_rate_limit import RedisRateLimiter

        return RedisRateLimiter(redis_url, limit, window_seconds)
    return RateLimiter(limit, window_seconds)
