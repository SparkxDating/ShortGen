"""Storage provider contract.

S3 and R2 implementations belong in later phases. Phase 1 ships
``LocalStorageProvider`` so the product runs without cloud infrastructure.
"""

from __future__ import annotations

from typing import Protocol


class StorageProvider(Protocol):
    def upload_file(self, local_path: str, object_key: str, content_type: str | None = None) -> str:
        """Copy a local file into storage and return the stored key."""

    def download_file(self, object_key: str, destination_path: str) -> str:
        """Download an object to a local path."""

    def delete_file(self, object_key: str) -> None:
        """Delete an object if it exists."""

    def get_public_url(self, object_key: str) -> str:
        """Return a URL the frontend can use in local/dev."""

    def get_signed_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        """Return a time-limited URL. Local provider returns the public URL."""

    def exists(self, object_key: str) -> bool:
        """True when the object is present."""
