from __future__ import annotations

from datetime import datetime

from pydantic import Field

from apps.api.schemas.common import ORMModel


class ProjectCreate(ORMModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)


class ProjectResponse(ORMModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime | None = None
