"""Select a storage implementation from configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.storage.local import LocalStorageProvider
from shared.storage.storage_provider import StorageProvider


def create_storage_provider(
    provider: str,
    storage_path: str | Path,
    public_base_url: str = "/storage",
    **kwargs: Any,
) -> StorageProvider:
    name = (provider or "local").strip().lower()
    if name == "local":
        return LocalStorageProvider(storage_path, public_base_url=public_base_url or "/storage")
    if name == "s3":
        from shared.storage.s3 import S3StorageProvider

        return S3StorageProvider(
            bucket=str(kwargs.get("bucket") or ""),
            region=str(kwargs.get("region") or "us-east-1"),
            endpoint_url=kwargs.get("endpoint_url") or None,
            access_key=kwargs.get("access_key") or None,
            secret_key=kwargs.get("secret_key") or None,
            public_base_url=kwargs.get("public_base_url") or None,
        )
    if name == "r2":
        from shared.storage.r2 import R2StorageProvider

        return R2StorageProvider(
            bucket=str(kwargs.get("bucket") or ""),
            account_id=kwargs.get("account_id") or None,
            endpoint_url=kwargs.get("endpoint_url") or None,
            access_key=kwargs.get("access_key") or None,
            secret_key=kwargs.get("secret_key") or None,
            public_base_url=kwargs.get("public_base_url") or None,
        )
    raise ValueError(f"unsupported storage provider: {provider}")
