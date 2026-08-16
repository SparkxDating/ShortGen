"""S3-compatible storage abstraction. Local provider ships first."""

from shared.storage.factory import create_storage_provider
from shared.storage.storage_provider import StorageProvider

__all__ = ["StorageProvider", "create_storage_provider"]
