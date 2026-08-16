"""Shared FastAPI dependencies for the SaaS API."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Request

from apps.api.config import get_settings
from shared.queue.factory import create_job_queue
from shared.queue.interface import JobQueue
from shared.storage.factory import create_storage_provider
from shared.storage.storage_provider import StorageProvider


@lru_cache(maxsize=1)
def get_queue() -> JobQueue:
    settings = get_settings()
    force_memory = settings.redis_url.startswith("memory://") or settings.environment == "test"
    try:
        return create_job_queue(settings.redis_url, force_memory=force_memory)
    except Exception:
        # Local development must work without Redis.
        return create_job_queue(force_memory=True)


@lru_cache(maxsize=1)
def get_storage() -> StorageProvider:
    settings = get_settings()
    return create_storage_provider(
        settings.storage_provider,
        settings.storage_path,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        public_base_url=settings.s3_public_base_url or None,
        account_id=settings.r2_account_id,
    )


def queue_from_app(request: Request) -> JobQueue:
    return getattr(request.app.state, "queue", None) or get_queue()
