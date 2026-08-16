"""Filesystem storage that keeps the SaaS usable without S3/R2."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from urllib.parse import quote

from shared.security.filenames import safe_object_key


class LocalStorageProvider:
    def __init__(self, root: str | Path, public_base_url: str = "/storage") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_base_url = (public_base_url or "/storage").rstrip("/")

    def _resolve(self, object_key: str) -> Path:
        key = safe_object_key(object_key)
        destination = (self.root / key).resolve()
        if not str(destination).startswith(str(self.root)):
            raise ValueError("object key escapes storage root")
        return destination

    def upload_file(self, local_path: str, object_key: str, content_type: str | None = None) -> str:
        source = Path(local_path)
        if not source.is_file():
            raise FileNotFoundError(f"local file does not exist: {local_path}")
        destination = self._resolve(object_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return safe_object_key(object_key)

    def upload_bytes(self, data: bytes, object_key: str, content_type: str | None = None) -> str:
        destination = self._resolve(object_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return safe_object_key(object_key)

    def download_file(self, object_key: str, destination_path: str) -> str:
        source = self._resolve(object_key)
        if not source.is_file():
            raise FileNotFoundError(f"object not found: {object_key}")
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return str(destination)

    def delete_file(self, object_key: str) -> None:
        path = self._resolve(object_key)
        if path.is_file():
            path.unlink()

    def get_public_url(self, object_key: str) -> str:
        key = safe_object_key(object_key)
        encoded = "/".join(quote(part) for part in key.split("/"))
        return f"{self.public_base_url}/{encoded}"

    def get_signed_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        # Local files are served by the API; a signed URL is the public path.
        return self.get_public_url(object_key)

    def exists(self, object_key: str) -> bool:
        return self._resolve(object_key).is_file()

    def absolute_path(self, object_key: str) -> Path:
        return self._resolve(object_key)
