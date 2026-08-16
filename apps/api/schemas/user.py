from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field

from apps.api.schemas.common import ORMModel


class UserResponse(ORMModel):
    id: str
    email: EmailStr
    name: str
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class UserUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=1000)
