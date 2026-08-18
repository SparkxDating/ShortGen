from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_engine.costs import credits_for_visual
from apps.api.config import get_settings
from apps.api.models.asset import Asset
from apps.api.models.job import Job, JobStatus, JobType
from apps.api.models.scene import VideoScene
from apps.api.models.video import Video, VideoStatus
from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.director import ScenePatch, SceneResponse
from apps.api.services import credit_service, outbox_service, workspace_service
from apps.api.services.director_service import scene_to_response
from apps.api.services.errors import NotFoundError, ServiceError
from shared.queue.interface import JobQueue


def _video(db: Session, video_id: str, user_id: str, role: WorkspaceRole = WorkspaceRole.viewer) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("video not found")
    workspace_service.require_membership(db, video.workspace_id, user_id, role)
    return video


def list_scenes(db: Session, video_id: str, user_id: str) -> list[SceneResponse]:
    video = _video(db, video_id, user_id)
    rows = list(
        db.scalars(select(VideoScene).where(VideoScene.video_id == video.id).order_by(VideoScene.order.asc())).all()
    )
    return [scene_to_response(row) for row in rows]


def get_scene(db: Session, video_id: str, scene_id: str, user_id: str) -> SceneResponse:
    video = _video(db, video_id, user_id)
    row = db.get(VideoScene, scene_id)
    if row is None or row.video_id != video.id:
        raise NotFoundError("scene not found")
    return scene_to_response(row)


def patch_scene(db: Session, video_id: str, scene_id: str, user_id: str, payload: ScenePatch) -> SceneResponse:
    video = _video(db, video_id, user_id, WorkspaceRole.editor)
    row = db.get(VideoScene, scene_id)
    if row is None or row.video_id != video.id:
        raise NotFoundError("scene not found")
    if payload.narration is not None:
        row.narration = payload.narration
        row.caption = payload.narration[:180]
    if payload.visual_type is not None:
        row.visual_type = payload.visual_type
    if payload.visual_prompt is not None:
        row.visual_prompt = payload.visual_prompt
    if payload.visual_query is not None:
        row.visual_query = payload.visual_query
    if payload.duration is not None:
        row.duration = payload.duration
    if payload.asset_id is not None:
        asset = db.get(Asset, payload.asset_id)
        if asset is None or asset.workspace_id != video.workspace_id:
            raise ServiceError("asset not found", status_code=404)
        row.asset_id = payload.asset_id
    db.commit()
    db.refresh(row)
    return scene_to_response(row)


def regenerate_scene(db: Session, queue: JobQueue, video_id: str, scene_id: str, user_id: str) -> SceneResponse:
    video = _video(db, video_id, user_id, WorkspaceRole.editor)
    row = db.get(VideoScene, scene_id)
    if row is None or row.video_id != video.id:
        raise NotFoundError("scene not found")
    settings = get_settings()
    if row.visual_type == "ai_video" and not settings.ai_video_enabled:
        raise ServiceError("AI video generation is temporarily unavailable", status_code=409)
    cost = credits_for_visual(row.visual_type)
    job = Job(
        workspace_id=video.workspace_id,
        video_id=video.id,
        job_type=JobType.generate_scene.value,
        status=JobStatus.QUEUED.value,
        current_stage="QUEUED",
        input_data={
            "scene_id": row.id,
            "visual_type": row.visual_type,
            "credit_cost": cost,
            "workspace_id": video.workspace_id,
            "video_id": video.id,
        },
    )
    db.add(job)
    db.flush()
    if cost:
        credit_service.reserve(db, video.workspace_id, job.id, cost, created_by=user_id)
    row.status = "queued"
    if video.status == VideoStatus.completed.value:
        video.status = VideoStatus.processing.value
    outbox_service.enqueue_pending(db, job.id, job.input_data or {})
    db.commit()
    try:
        outbox_service.dispatch(db, queue, job.id)
    except Exception:
        pass
    db.refresh(row)
    return scene_to_response(row)
