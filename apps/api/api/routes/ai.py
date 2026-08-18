from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.database.session import get_db
from apps.api.models.scene import ProviderGeneration
from apps.api.models.user import User
from apps.api.schemas.director import CapabilitiesResponse
from apps.api.services import director_service
from sqlalchemy import select

router = APIRouter()


@router.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities(current_user: User = Depends(get_current_user)) -> CapabilitiesResponse:
    return director_service.capabilities()


@router.post("/webhooks/replicate")
async def replicate_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    import hmac
    import os

    body = await request.body()
    secret = (os.getenv("REPLICATE_WEBHOOK_SECRET") or "").strip()
    if secret:
        signature = request.headers.get("webhook-signature") or ""
        if not hmac.compare_digest(signature, hmac.new(secret.encode(), body, "sha256").hexdigest()):
            from apps.api.services.errors import ServiceError

            raise ServiceError("invalid replicate webhook", status_code=400)
    payload = await request.json()
    job_id = str(payload.get("id") or "")
    status = str(payload.get("status") or "")
    if not job_id:
        return {"status": "ignored"}
    row = db.scalar(select(ProviderGeneration).where(ProviderGeneration.provider_generation_id == job_id))
    if row:
        mapped = {
            "succeeded": "COMPLETED",
            "failed": "FAILED",
            "canceled": "CANCELLED",
            "processing": "PROCESSING",
        }.get(status.lower(), row.status)
        row.status = mapped
        db.commit()
    return {"status": "ok"}
