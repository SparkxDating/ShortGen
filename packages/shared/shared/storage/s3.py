"""S3-compatible storage. Works with AWS S3 and MinIO.

Phase 1 shipped a stub so the product could run locally. Phase 2 implements
the provider without making AWS required. Local storage remains the default.
"""

from __future__ import annotations

from pathlib import Path

from shared.security.filenames import safe_object_key


class S3StorageProvider:
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        public_base_url: str | None = None,
        addressing_style: str = "auto",
    ) -> None:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for STORAGE_PROVIDER=s3. "
                "Install it or keep STORAGE_PROVIDER=local."
            ) from exc
        if not bucket:
            raise RuntimeError("S3_BUCKET must be set when STORAGE_PROVIDER=s3")
        session_kwargs: dict = {"region_name": region or "us-east-1"}
        if access_key and secret_key:
            session_kwargs["aws_access_key_id"] = access_key
            session_kwargs["aws_secret_access_key"] = secret_key
        extra: dict = {}
        if endpoint_url:
            extra["endpoint_url"] = endpoint_url
        extra["config"] = Config(s3={"addressing_style": addressing_style})
        self.client = boto3.client("s3", **session_kwargs, **extra)
        self.bucket = bucket
        self.public_base_url = (public_base_url or "").rstrip("/")
        self.endpoint_url = (endpoint_url or "").rstrip("/")

    def upload_file(self, local_path: str, object_key: str, content_type: str | None = None) -> str:
        key = safe_object_key(object_key)
        extra = {"ContentType": content_type} if content_type else {}
        self.client.upload_file(local_path, self.bucket, key, ExtraArgs=extra or None)
        return key

    def upload_bytes(self, data: bytes, object_key: str, content_type: str | None = None) -> str:
        key = safe_object_key(object_key)
        extra = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)
        return key

    def download_file(self, object_key: str, destination_path: str) -> str:
        key = safe_object_key(object_key)
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(destination))
        return str(destination)

    def delete_file(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=safe_object_key(object_key))

    def get_public_url(self, object_key: str) -> str:
        # Private buckets: never invent a permanent public URL.
        if self.public_base_url:
            return self.get_signed_url(object_key)
        return self.get_signed_url(object_key)

    def get_signed_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": safe_object_key(object_key)},
            ExpiresIn=expires_seconds,
        )

    def exists(self, object_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=safe_object_key(object_key))
            return True
        except Exception:
            return False
