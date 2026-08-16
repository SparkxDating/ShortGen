"""Cloudflare R2 uses the S3 API. This provider is a thin alias."""

from __future__ import annotations

from shared.storage.s3 import S3StorageProvider


class R2StorageProvider(S3StorageProvider):
    def __init__(
        self,
        bucket: str,
        account_id: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        public_base_url: str | None = None,
    ) -> None:
        endpoint = endpoint_url
        if not endpoint and account_id:
            endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        if not endpoint:
            raise RuntimeError("S3_ENDPOINT_URL or R2_ACCOUNT_ID is required for STORAGE_PROVIDER=r2")
        super().__init__(
            bucket=bucket,
            region="auto",
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            public_base_url=public_base_url,
            addressing_style="path",
        )
