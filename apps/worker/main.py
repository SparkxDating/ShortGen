"""Long-running worker process.

API
 → create video + job
 → enqueue
 → this worker
 → MoneyPrinterTurboGenerationAdapter
 → existing app.services.task pipeline
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bootstrap import ensure_sys_path

ensure_sys_path()

from apps.api.config import get_settings
from apps.api.database.session import SessionLocal, init_db
from apps.api.api.deps import get_queue, get_storage
from apps.worker.runner import JobRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("saas.worker")

_running = True


def _stop(*_: object) -> None:
    global _running
    _running = False


def main() -> None:
    settings = get_settings()
    if settings.auto_create_schema:
        init_db()
    queue = get_queue()
    storage = get_storage()
    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)
    logger.info("worker started redis=%s storage=%s", settings.redis_url, settings.storage_provider)
    idle_ticks = 0
    while _running:
        db = SessionLocal()
        try:
            if idle_ticks % 6 == 0:
                from apps.api.services import job_recovery, outbox_service

                outbox_service.dispatch(db, queue)
                job_recovery.recover_stale_jobs(db, queue)
        except Exception:
            logger.exception("worker maintenance failed")
        finally:
            db.close()
        job = queue.dequeue_job(timeout_seconds=5)
        idle_ticks += 1
        if job is None:
            continue
        db = SessionLocal()
        try:
            runner = JobRunner(db, queue, storage)
            runner.process_job(job.job_id)
        except Exception:
            logger.exception("failed to process job %s", job.job_id)
        finally:
            db.close()
    logger.info("worker stopped")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
