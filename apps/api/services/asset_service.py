from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.models.asset import Asset
from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.asset import AssetResponse
from apps.api.services import workspace_service
from apps.api.services.errors import NotFoundError, ServiceError
from shared.security.filenames import is_allowed_upload, safe_filename
from shared.storage.storage_provider import StorageProvider

ALLOWED_UPLOADS = {
    ".mp4": "video",
    ".mov": "video",
    ".webm": "video",
    ".mkv": "video",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
}
CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}


def list_assets(db: Session, user_id: str, workspace_id: str) -> list[AssetResponse]:
    workspace_service.require_membership(db, workspace_id, user_id)
    assets = list(
        db.scalars(
            select(Asset).where(Asset.workspace_id == workspace_id).order_by(Asset.created_at.desc())
        ).all()
    )
    return [AssetResponse.model_validate(asset) for asset in assets]


def get_asset(db: Session, asset_id: str, user_id: str) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("asset not found")
    workspace_service.require_membership(db, asset.workspace_id, user_id)
    return asset


def create_asset(
    db: Session,
    storage: StorageProvider,
    user_id: str,
    workspace_id: str,
    filename: str,
    content: bytes,
    content_type: str | None,
) -> AssetResponse:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.editor)
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise ServiceError("file exceeds the maximum upload size", status_code=413)
    if not content:
        raise ServiceError("empty files are not allowed", status_code=400)
    safe_name = safe_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_UPLOADS or not is_allowed_upload(safe_name, set(ALLOWED_UPLOADS)):
        raise ServiceError("unsupported file type", status_code=400)
    kind = ALLOWED_UPLOADS[suffix]
    key = f"workspaces/{workspace_id}/assets/{uuid4().hex}-{safe_name}"
    upload_bytes = getattr(storage, "upload_bytes", None)
    if callable(upload_bytes):
        stored = upload_bytes(content, key, content_type or CONTENT_TYPES.get(suffix))
    else:
        raise ServiceError("storage provider cannot accept uploads", status_code=500)
    asset = Asset(
        workspace_id=workspace_id,
        name=Path(safe_name).stem[:160] or "asset",
        kind=kind,
        object_key=stored,
        public_url=storage.get_public_url(stored),
        content_type=content_type or CONTENT_TYPES.get(suffix, "application/octet-stream"),
        size_bytes=len(content),
        original_filename=safe_name,
        created_by=user_id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return AssetResponse.model_validate(asset)


def delete_asset(db: Session, storage: StorageProvider, asset_id: str, user_id: str) -> None:
    asset = get_asset(db, asset_id, user_id)
    workspace_service.require_membership(db, asset.workspace_id, user_id, WorkspaceRole.admin)
    storage.delete_file(asset.object_key)
    db.delete(asset)
    db.commit()
