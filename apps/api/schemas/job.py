from __future__ import annotations

from datetime import datetime
from typing import Any

from apps.api.schemas.common import ORMModel


class JobResponse(ORMModel):
    id: str
    workspace_id: str
    video_id: str
    job_type: str
    status: str
    progress: int
    current_stage: str
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    retry_count: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobCancelResponse(ORMModel):
    id: str
    status: str
    message: str
