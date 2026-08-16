from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from apps.api.schemas.common import ORMModel


class TemplateCreate(ORMModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    config: dict[str, Any] = Field(default_factory=dict)


class TemplateResponse(ORMModel):
    id: str
    workspace_id: str | None
    name: str
    description: str | None = None
    is_system: bool
    config: dict[str, Any]
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
