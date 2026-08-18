from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_user
from apps.api.config import get_settings
from apps.api.database.session import get_db
from apps.api.models.user import User
from apps.api.schemas.billing import (
    BillingStatusResponse,
    CheckoutRequest,
    CheckoutResponse,
    CreditPackResponse,
    DevGrantRequest,
    EstimateResponse,
    LedgerEntryResponse,
    PlanResponse,
    UsageResponse,
)
from apps.api.services import billing_service, credit_service, workspace_service

router = APIRouter()


@router.get("/status", response_model=BillingStatusResponse)
def billing_status() -> BillingStatusResponse:
    settings = get_settings()
    provider = settings.billing_provider
    webhook = bool(
        (provider == "stripe" and settings.stripe_webhook_secret)
        or (provider == "razorpay" and settings.razorpay_webhook_secret)
    )
    live_ready = provider in {"stripe", "razorpay"} and webhook and bool(
        settings.stripe_secret_key if provider == "stripe" else settings.razorpay_key_secret
    )
    if provider == "local":
        message = "Local billing is active. Credits are granted without a card network."
    elif live_ready:
        message = f"{provider} is live. Credits are added only after a verified webhook."
    else:
        message = f"{provider} is selected but keys or webhook secret are missing."
    return BillingStatusResponse(
        provider=provider,
        live_ready=live_ready,
        webhook_configured=webhook,
        environment=settings.environment,
        message=message,
    )


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlanResponse]:
    return billing_service.list_plans(db)


@router.get("/packs", response_model=list[CreditPackResponse])
def list_packs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CreditPackResponse]:
    return billing_service.list_packs(db)


@router.get("/usage", response_model=UsageResponse)
def usage(
    workspace_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageResponse:
    workspace_service.require_membership(db, workspace_id, current_user.id)
    return credit_service.get_usage(db, workspace_id)


@router.get("/estimate", response_model=EstimateResponse)
def estimate(
    duration: int = Query(default=30, ge=5, le=300),
    resolution: str = Query(default="1080p"),
    current_user: User = Depends(get_current_user),
) -> EstimateResponse:
    return credit_service.estimate_payload(duration, resolution)


@router.get("/ledger", response_model=list[LedgerEntryResponse])
def ledger(
    workspace_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LedgerEntryResponse]:
    return billing_service.list_ledger(db, workspace_id, current_user.id)


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    payload: CheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    settings = get_settings()
    origin = request.headers.get("origin") or (
        settings.cors_origins[0] if settings.cors_origins else "http://127.0.0.1:3000"
    )
    return billing_service.checkout(
        db,
        current_user.id,
        payload.workspace_id,
        payload.kind,
        payload.item_id,
        success_url=f"{origin}/billing?status=success",
        cancel_url=f"{origin}/billing?status=cancel",
    )


@router.post("/dev/grant")
def dev_grant(
    payload: DevGrantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    billing_service.dev_grant(db, payload.workspace_id, current_user.id, payload.credits, payload.description)
    return {"status": "ok"}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    return billing_service.handle_webhook(db, "stripe", body, headers)


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    return billing_service.handle_webhook(db, "razorpay", body, headers)
