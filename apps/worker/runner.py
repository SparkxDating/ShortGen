"""Process one generation job using the existing MoneyPrinterTurbo engine."""

from __future__ import annotations

import logging
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.models.job import Job, JobStatus
from apps.api.models.video import Video, VideoStatus
from shared.queue.interface import JobQueue
from shared.storage.storage_provider import StorageProvider
from video_engine.generation_adapter import (
    GenerationCancelled,
    GenerationError,
    MoneyPrinterTurboGenerationAdapter,
)
from video_engine.stages import stage_progress

logger = logging.getLogger("saas.worker")

AdapterFactory = Callable[[], MoneyPrinterTurboGenerationAdapter]


class JobRunner:
    def __init__(
        self,
        db: Session,
        queue: JobQueue,
        storage: StorageProvider,
        adapter_factory: AdapterFactory | None = None,
    ) -> None:
        self.db = db
        self.queue = queue
        self.storage = storage
        self.adapter_factory = adapter_factory or MoneyPrinterTurboGenerationAdapter
        self.worker_id = f"{socket.gethostname()}:{uuid4().hex[:8]}"

    def process_job(self, job_id: str) -> Job:
        job = self.db.get(Job, job_id)
        if job is None:
            raise RuntimeError(f"job not found: {job_id}")
        if job.status in {JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
            return job
        if job.status == JobStatus.CANCELLED.value or self.queue.is_cancelled(job_id):
            job.status = JobStatus.CANCELLED.value
            job.current_stage = "CANCELLED"
            self.db.commit()
            return job
        if (
            job.status == JobStatus.RUNNING.value
            and job.heartbeat_at
            and (datetime.now(timezone.utc) - job.heartbeat_at).total_seconds() < 60
            and job.worker_id
            and job.worker_id != self.worker_id
        ):
            logger.info("skip concurrent lease job_id=%s worker=%s", job.id, job.worker_id)
            return job

        now = datetime.now(timezone.utc)
        job.status = JobStatus.RUNNING.value
        job.started_at = now
        job.attempt_started_at = now
        job.heartbeat_at = now
        job.worker_id = self.worker_id
        job.current_stage = "ANALYZING"
        job.progress = stage_progress("ANALYZING")
        job.error_message = None
        video = self.db.get(Video, job.video_id)
        if video:
            video.status = VideoStatus.processing.value
            video.progress = job.progress
        self.db.commit()
        self.queue.set_job_status(job.id, "RUNNING")

        adapter = self.adapter_factory()

        def on_progress(stage: str, progress: int, extra: dict[str, Any] | None = None) -> None:
            self.db.refresh(job)
            if self.queue.is_cancelled(job.id) or job.status == JobStatus.CANCELLED.value:
                raise GenerationCancelled("generation cancelled")
            job.current_stage = stage
            job.progress = progress
            job.heartbeat_at = datetime.now(timezone.utc)
            if video:
                video.progress = progress
                video.status = VideoStatus.processing.value
            self.db.commit()
            logger.info("job_stage job_id=%s workspace_id=%s stage=%s progress=%s", job.id, job.workspace_id, stage, progress)

        try:
            payload = dict(job.input_data or {})
            payload.update(self._material_payload(job, payload))
            result = adapter.create_video(
                payload,
                task_id=f"saas-{job.id}",
                on_progress=on_progress,
                should_cancel=lambda: self.queue.is_cancelled(job.id),
            )
            video_url = None
            thumbnail_url = None
            on_progress("UPLOADING", stage_progress("UPLOADING"))
            if result.primary_video_path:
                key = f"workspaces/{job.workspace_id}/videos/{job.video_id}/final.mp4"
                stored = self.storage.upload_file(result.primary_video_path, key, "video/mp4")
                signer = getattr(self.storage, "get_signed_url", None)
                video_url = signer(stored) if callable(signer) else self.storage.get_public_url(stored)
            job.status = JobStatus.COMPLETED.value
            job.current_stage = "COMPLETED"
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            job.output_data = {
                "task_id": result.task_id,
                "script": result.script,
                "video_paths": result.video_paths,
                "video_url": video_url,
            }
            if video:
                video.status = VideoStatus.completed.value
                video.progress = 100
                video.video_url = video_url
                video.thumbnail_url = thumbnail_url
                if result.audio_duration:
                    video.duration = float(result.audio_duration)
            self.queue.set_job_status(job.id, "COMPLETED")
            from apps.api.services import credit_service

            credit_service.capture(self.db, job.workspace_id, job.id, retry_count=job.retry_count or 0)
            self.db.commit()
            logger.info("job_completed job_id=%s workspace_id=%s video_id=%s", job.id, job.workspace_id, job.video_id)
            return job
        except GenerationCancelled:
            job.status = JobStatus.CANCELLED.value
            job.current_stage = "CANCELLED"
            job.completed_at = datetime.now(timezone.utc)
            if video and video.status != VideoStatus.completed.value:
                video.status = VideoStatus.cancelled.value
            self.queue.set_job_status(job.id, "CANCELLED")
            from apps.api.services import credit_service

            credit_service.refund(
                self.db, job.workspace_id, job.id, "Generation cancelled", retry_count=job.retry_count or 0
            )
            self.db.commit()
            logger.info("job_cancelled job_id=%s workspace_id=%s", job.id, job.workspace_id)
            return job
        except (GenerationError, Exception) as exc:
            logger.exception("job_failed job_id=%s workspace_id=%s", job.id, job.workspace_id)
            job.status = JobStatus.FAILED.value
            job.current_stage = "FAILED"
            job.error_message = str(exc) or "generation failed"
            job.completed_at = datetime.now(timezone.utc)
            if video:
                video.status = VideoStatus.failed.value
            self.queue.set_job_status(job.id, "FAILED")
            from apps.api.services import credit_service

            credit_service.refund(
                self.db, job.workspace_id, job.id, "Generation failed", retry_count=job.retry_count or 0
            )
            self.db.commit()
            return job
        finally:
            self._cleanup_work_dir(job_id)

    def _cleanup_work_dir(self, job_id: str) -> None:
        from apps.api.bootstrap import REPO_ROOT

        root = (REPO_ROOT / "storage" / "saas-work").resolve()
        target = (root / job_id).resolve()
        try:
            if str(target).startswith(str(root)) and target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
        except Exception:
            logger.warning("temp cleanup skipped job_id=%s", job_id)

    def _material_payload(self, job: Job, payload: dict[str, Any]) -> dict[str, Any]:
        asset_ids = list(payload.get("asset_ids") or [])
        if not asset_ids:
            return {}
        from apps.api.models.asset import Asset
        from apps.api.bootstrap import REPO_ROOT
        from shared.security.filenames import safe_filename

        material_dir = REPO_ROOT / "storage" / "saas-work" / job.id
        material_dir.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []
        for asset_id in asset_ids:
            asset = self.db.get(Asset, asset_id)
            if asset is None or asset.workspace_id != job.workspace_id:
                raise GenerationError("a selected asset is not available in this workspace")
            destination = material_dir / f"{asset.id}-{safe_filename(asset.original_filename)}"
            self.storage.download_file(asset.object_key, str(destination))
            paths.append(str(destination))
        return {"local_material_paths": paths, "visual_source": "local"}
