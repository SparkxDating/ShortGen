"""Social publish wrapper around the existing Upload-Post service.

This does not add a second uploader. It calls app.services.upload_post
and never posts when that integration is unconfigured.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.models.video import Video, VideoStatus
from apps.api.models.workspace import WorkspaceRole
from apps.api.services import workspace_service
from apps.api.services.errors import NotFoundError, ServiceError
from shared.security.filenames import safe_object_key


def _local_video_path(video: Video) -> str | None:
    url = video.video_url or ""
    if not url:
        return None
    prefix = "/storage/"
    if url.startswith(prefix):
        key = safe_object_key(url[len(prefix) :])
        settings = get_settings()
        path = Path(settings.storage_path) / key
        if path.is_file():
            return str(path)
    return None


def publish_video(
    db: Session,
    video_id: str,
    user_id: str,
    platforms: list[str] | None = None,
) -> dict:
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("video not found")
    workspace_service.require_membership(db, video.workspace_id, user_id, WorkspaceRole.editor)
    if video.status != VideoStatus.completed.value:
        raise ServiceError("only a completed video can be published")
    path = _local_video_path(video)
    if not path:
        raise ServiceError("video file is not available on local storage")

    from app.services.upload_post import UploadPostService

    service = UploadPostService()
    result = service.upload_video(
        video_path=path,
        title=video.title,
        platforms=platforms,
    )
    return {
        "video_id": video.id,
        "success": bool(result.get("success")),
        "configured": service.is_configured(),
        "platforms": platforms or service.platforms,
        "error": result.get("error"),
        "raw": result,
    }
