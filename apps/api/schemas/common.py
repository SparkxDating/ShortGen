from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str


class MessageResponse(BaseModel):
    message: str


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None
