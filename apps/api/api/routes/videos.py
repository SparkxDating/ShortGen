from fastapi import APIRouter, Depends, Header, Query, Request, status
from pydantic import Field
from sqlalchemy.orm import Session

from apps.api.api.deps import queue_from_app
from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.common import ORMModel
from apps.api.schemas.video import VideoCreate, VideoResponse
from apps.api.services import publish_service, video_service


class PublishRequest(ORMModel):
    platforms: list[str] = Field(default_factory=list)

router = APIRouter()


@router.get("", response_model=list[VideoResponse])
def list_videos(
    workspace_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VideoResponse]:
    return video_service.list_videos(db, current_user.id, workspace_id, project_id)


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def create_video(
    payload: VideoCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> VideoResponse:
    return video_service.create_video(
        db,
        queue_from_app(request),
        current_user.id,
        payload,
        idempotency_key=idempotency_key,
    )


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoResponse:
    return video_service.get_video(db, video_id, current_user.id)


@router.post("/{video_id}/publish")
def publish_video(
    video_id: str,
    payload: PublishRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    platforms = [item for item in (payload.platforms if payload else []) if item]
    return publish_service.publish_video(db, video_id, current_user.id, platforms or None)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    video_service.delete_video(db, video_id, current_user.id)
