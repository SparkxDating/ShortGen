from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from apps.api.schemas.common import ORMModel

RoleName = Literal["owner", "admin", "editor", "viewer"]


class MemberResponse(ORMModel):
    id: str
    user_id: str
    email: str
    name: str
    role: str
    created_at: datetime


class MemberRoleUpdate(ORMModel):
    role: RoleName


class InviteCreate(ORMModel):
    email: EmailStr
    role: Literal["admin", "editor", "viewer"] = "editor"


class InviteResponse(ORMModel):
    id: str
    workspace_id: str
    email: str
    role: str
    status: str
    token: str
    invited_by: str
    expires_at: datetime
    created_at: datetime


class InvitePreview(ORMModel):
    workspace_name: str
    email: str
    role: str
    status: str


class InviteAccept(ORMModel):
    token: str = Field(min_length=8, max_length=120)
