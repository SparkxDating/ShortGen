"""Structured Director plans. Does not call a video vendor."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ai_engine.director.planner import plan_video
from ai_engine.director.schema import VideoPlan
from apps.api.config import get_settings
from apps.api.models.asset import Asset
from apps.api.models.scene import VideoScene
from apps.api.models.video import Video, VideoStatus
from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.director import (
    CapabilitiesResponse,
    DirectorPlanRequest,
    DirectorPlanResponse,
    SceneResponse,
    VideoPlanOut,
)
from apps.api.services import script_service, workspace_service
from apps.api.services.errors import ServiceError
from ai_engine.router import AIProviderRouter


def capabilities() -> CapabilitiesResponse:
    settings = get_settings()
    router = AIProviderRouter(
        environment=settings.environment,
        video_provider=settings.ai_video_provider,
        image_provider=settings.ai_image_provider,
        video_enabled=settings.ai_video_enabled,
    )
    video = router.video_capabilities()
    image = router.image_capabilities()
    providers = []
    if video:
        providers.append(
            {
                "name": video.name,
                "kind": "ai_video",
                "models": video.models,
                "aspect_ratios": video.aspect_ratios,
                "durations": video.durations,
            }
        )
    if image:
        providers.append(
            {
                "name": image.name,
                "kind": "ai_image",
                "models": image.models,
                "aspect_ratios": image.aspect_ratios,
                "durations": image.durations,
            }
        )
    message = ""
    if not settings.ai_video_enabled:
        message = "AI video generation is temporarily unavailable."
    return CapabilitiesResponse(
        ai_video=bool(settings.ai_video_enabled and video),
        ai_image=bool(image),
        message=message,
        providers=providers,
    )


def create_plan(db: Session, user_id: str, payload: DirectorPlanRequest) -> DirectorPlanResponse:
    workspace_service.require_membership(db, payload.workspace_id, user_id, WorkspaceRole.editor)
    preview = script_service.preview_script(
        db,
        user_id,
        payload.workspace_id,
        payload.topic,
        payload.video_language,
    )
    asset_ids = []
    for asset_id in payload.asset_ids:
        asset = db.get(Asset, asset_id)
        if asset is None or asset.workspace_id != payload.workspace_id:
            raise ServiceError("asset not found", status_code=404)
        asset_ids.append(asset_id)
    video_plan = plan_video(
        topic=payload.topic,
        script=preview.script,
        duration=payload.duration,
        language=payload.video_language,
        aspect_ratio=payload.aspect_ratio,
        resolution=payload.resolution,
        style=payload.style,
        tone=payload.tone,
        target_platform=payload.target_platform,
        visual_mode=payload.visual_mode,
        asset_ids=asset_ids,
    )
    video_id = None
    if payload.project_id:
        video_id = _persist_draft(db, user_id, payload, video_plan)
    summary = _plain_plan(payload.topic, preview.script, video_plan)
    return DirectorPlanResponse(
        topic=payload.topic.strip(),
        script=preview.script,
        plan=summary,
        renderer="moneyprinterturbo",
        video_plan=VideoPlanOut.model_validate(video_plan.model_dump()),
        video_id=video_id,
        source=preview.source or "local",
        warning=preview.warning or "",
    )


def persist_plan(db: Session, video: Video, plan: VideoPlan) -> list[VideoScene]:
    from sqlalchemy import delete

    db.execute(delete(VideoScene).where(VideoScene.video_id == video.id))
    rows: list[VideoScene] = []
    for scene in plan.scenes:
        row = VideoScene(
            video_id=video.id,
            workspace_id=video.workspace_id,
            order=scene.order,
            duration=scene.duration,
            narration=scene.narration,
            visual_type=scene.visual_type,
            visual_prompt=scene.visual_prompt,
            visual_query=scene.visual_query,
            caption=scene.caption or scene.narration[:180],
            provider=scene.generation_provider,
            status="pending",
            asset_id=scene.asset_id,
        )
        db.add(row)
        rows.append(row)
    video.plan_json = plan.model_dump()
    video.visual_mode = plan.visual_mode
    db.flush()
    return rows


def scene_to_response(row: VideoScene) -> SceneResponse:
    return SceneResponse.model_validate(row)


def _persist_draft(db: Session, user_id: str, payload: DirectorPlanRequest, plan: VideoPlan) -> str:
    from apps.api.models.project import Project

    project = db.get(Project, payload.project_id)
    if project is None or project.workspace_id != payload.workspace_id:
        raise ServiceError("project not found", status_code=404)
    video = Video(
        workspace_id=payload.workspace_id,
        project_id=project.id,
        title=plan.title[:200],
        status=VideoStatus.draft.value,
        progress=0,
        duration=float(plan.duration),
        aspect_ratio=plan.aspect_ratio,
        resolution=plan.resolution,
        created_by=user_id,
        visual_mode=plan.visual_mode,
        plan_json=plan.model_dump(),
    )
    db.add(video)
    db.flush()
    persist_plan(db, video, plan)
    db.commit()
    return video.id


def _plain_plan(topic: str, script: str, plan: VideoPlan) -> str:
    lines = [
        f"Hook\n{topic.strip()}\n",
        f"Narration\n{script}\n",
        "Scenes",
    ]
    for scene in plan.scenes:
        lines.append(f"{scene.order}. [{scene.visual_type}] {scene.duration:.0f}s — {scene.narration[:140]}")
    lines.append("\nRenderer\nExisting ShortGen engine (MoneyPrinterTurbo). AI clips are scene inputs only.")
    return "\n".join(lines)
