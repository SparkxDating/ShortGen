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

ALLOWED_PLATFORMS = {"tiktok", "instagram", "youtube", "youtube-shorts"}


def _normalize_platforms(platforms: list[str] | None) -> list[str] | None:
    if not platforms:
        return None
    seen: list[str] = []
    for item in platforms:
        name = str(item).strip().lower()
        if name == "ig":
            name = "instagram"
        if name == "yt":
            name = "youtube"
        if name in ALLOWED_PLATFORMS and name not in seen:
            seen.append(name)
    return seen or None


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

    chosen = _normalize_platforms(platforms)
    service = UploadPostService()
    if not service.is_configured():
        return {
            "video_id": video.id,
            "success": False,
            "configured": False,
            "platforms": chosen or list(service.platforms or []),
            "error": "Connect Upload-Post in Settings (API key + username) and enable publishing.",
            "raw": None,
        }
    youtube_extra = None
    targets = chosen or list(service.platforms or [])
    if any(str(item).startswith("youtube") for item in targets):
        youtube_extra = {
            "youtube_title": (video.title or "ShortGen video")[:100],
            "youtube_description": video.title or "Created with ShortGen",
            "privacyStatus": str(getattr(service, "youtube_privacy_status", "public") or "public"),
        }
    result = service.upload_video(
        video_path=path,
        title=video.title,
        platforms=chosen,
        youtube_extra=youtube_extra,
    )
    return {
        "video_id": video.id,
        "success": bool(result.get("success")),
        "configured": True,
        "platforms": targets,
        "error": result.get("error") or result.get("message"),
        "raw": result,
    }
