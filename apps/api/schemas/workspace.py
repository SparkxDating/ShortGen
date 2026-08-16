from __future__ import annotations

from datetime import datetime

from pydantic import Field

from apps.api.schemas.common import ORMModel


class WorkspaceCreate(ORMModel):
    name: str = Field(min_length=1, max_length=120)


class WorkspaceResponse(ORMModel):
    id: str
    name: str
    slug: str
    owner_id: str
    role: str
    created_at: datetime
    updated_at: datetime | None = None
