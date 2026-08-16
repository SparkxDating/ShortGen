from __future__ import annotations

from datetime import datetime

from apps.api.schemas.common import ORMModel


class AssetResponse(ORMModel):
    id: str
    workspace_id: str
    name: str
    kind: str
    object_key: str
    public_url: str
    content_type: str
    size_bytes: int
    original_filename: str
    created_by: str
    created_at: datetime
