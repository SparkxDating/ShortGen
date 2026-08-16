"""Workspace credit wallet. Authorization is enforced by callers."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.models.billing import CreditLedger, CreditWallet, Plan, Subscription
from apps.api.models.job import Job
from apps.api.models.video import Video  # noqa: F401
from apps.api.schemas.billing import EstimateResponse, PlanResponse, UsageResponse
from apps.api.services.errors import ConflictError, ServiceError

FREE_PLAN_SLUG = "free"
SIGNUP_CREDITS = 100


class PaymentRequiredError(ServiceError):
    def __init__(self, message: str = "insufficient credits") -> None:
        super().__init__(message, status_code=402)


def estimate_credits(duration: int | float | None, resolution: str = "1080p") -> int:
    seconds = max(5, int(duration or 30))
    credits = max(10, math.ceil(seconds / 15) * 10)
    if resolution == "1080p":
        credits = math.ceil(credits * 1.25)
    return credits


def ensure_wallet(db: Session, workspace_id: str) -> CreditWallet:
    wallet = db.scalar(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
    if wallet:
        return wallet
    wallet = CreditWallet(workspace_id=workspace_id, balance=0, reserved=0)
    db.add(wallet)
    db.flush()
    return wallet


def _ledger_exists(db: Session, workspace_id: str, entry_type: str, reference_id: str) -> bool:
    return (
        db.scalar(
            select(CreditLedger.id).where(
                CreditLedger.workspace_id == workspace_id,
                CreditLedger.entry_type == entry_type,
                CreditLedger.reference_id == reference_id,
            )
        )
        is not None
    )


def _write_ledger(
    db: Session,
    wallet: CreditWallet,
    amount: int,
    entry_type: str,
    description: str,
    reference_type: str | None = None,
    reference_id: str | None = None,
    created_by: str | None = None,
) -> CreditLedger:
    entry = CreditLedger(
        workspace_id=wallet.workspace_id,
        amount=amount,
        balance_after=wallet.balance,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        created_by=created_by,
    )
    db.add(entry)
    db.flush()
    return entry


def grant(
    db: Session,
    workspace_id: str,
    credits: int,
    entry_type: str,
    description: str,
    reference_id: str | None = None,
    created_by: str | None = None,
) -> CreditWallet:
    if credits <= 0:
        raise ServiceError("credit grant must be positive")
    if reference_id and _ledger_exists(db, workspace_id, entry_type, reference_id):
        return ensure_wallet(db, workspace_id)
    wallet = ensure_wallet(db, workspace_id)
    wallet.balance += credits
    _write_ledger(
        db,
        wallet,
        credits,
        entry_type,
        description,
        reference_type=entry_type,
        reference_id=reference_id,
        created_by=created_by,
    )
    return wallet


def reservation_key(job_id: str, retry_count: int = 0) -> str:
    return f"{job_id}:r{retry_count}"


def reserve(
    db: Session,
    workspace_id: str,
    job_id: str,
    credits: int,
    created_by: str | None = None,
    retry_count: int = 0,
) -> CreditWallet:
    if credits <= 0:
        return ensure_wallet(db, workspace_id)
    reference_id = reservation_key(job_id, retry_count)
    if _ledger_exists(db, workspace_id, "reserve", reference_id):
        return ensure_wallet(db, workspace_id)
    wallet = ensure_wallet(db, workspace_id)
    if wallet.balance < credits:
        raise PaymentRequiredError(
            f"this video costs {credits} credits; workspace has {wallet.balance} available"
        )
    wallet.balance -= credits
    wallet.reserved += credits
    _write_ledger(
        db,
        wallet,
        -credits,
        "reserve",
        f"Reserved {credits} credits for generation",
        reference_type="job",
        reference_id=reference_id,
        created_by=created_by,
    )
    return wallet


def capture(db: Session, workspace_id: str, job_id: str, retry_count: int = 0) -> CreditWallet:
    reference_id = reservation_key(job_id, retry_count)
    if _ledger_exists(db, workspace_id, "capture", reference_id):
        return ensure_wallet(db, workspace_id)
    reserved_entry = db.scalar(
        select(CreditLedger).where(
            CreditLedger.workspace_id == workspace_id,
            CreditLedger.entry_type == "reserve",
            CreditLedger.reference_id == reference_id,
        )
    )
    wallet = ensure_wallet(db, workspace_id)
    if reserved_entry is None:
        return wallet
    credits = abs(reserved_entry.amount)
    wallet.reserved = max(0, wallet.reserved - credits)
    _write_ledger(
        db,
        wallet,
        0,
        "capture",
        f"Captured {credits} credits after successful generation",
        reference_type="job",
        reference_id=reference_id,
    )
    return wallet


def refund(
    db: Session,
    workspace_id: str,
    job_id: str,
    reason: str = "Generation did not complete",
    retry_count: int = 0,
) -> CreditWallet:
    reference_id = reservation_key(job_id, retry_count)
    if _ledger_exists(db, workspace_id, "refund", reference_id):
        return ensure_wallet(db, workspace_id)
    if _ledger_exists(db, workspace_id, "capture", reference_id):
        return ensure_wallet(db, workspace_id)
    reserved_entry = db.scalar(
        select(CreditLedger).where(
            CreditLedger.workspace_id == workspace_id,
            CreditLedger.entry_type == "reserve",
            CreditLedger.reference_id == reference_id,
        )
    )
    wallet = ensure_wallet(db, workspace_id)
    if reserved_entry is None:
        return wallet
    credits = abs(reserved_entry.amount)
    wallet.reserved = max(0, wallet.reserved - credits)
    wallet.balance += credits
    _write_ledger(
        db,
        wallet,
        credits,
        "refund",
        reason,
        reference_type="job",
        reference_id=reference_id,
    )
    return wallet


def provision_workspace(db: Session, workspace_id: str, created_by: str | None = None) -> None:
    ensure_wallet(db, workspace_id)
    free = db.scalar(select(Plan).where(Plan.slug == FREE_PLAN_SLUG))
    existing = db.scalar(select(Subscription).where(Subscription.workspace_id == workspace_id))
    if free and existing is None:
        db.add(
            Subscription(
                workspace_id=workspace_id,
                plan_id=free.id,
                status="active",
                provider="local",
            )
        )
    grant(
        db,
        workspace_id,
        SIGNUP_CREDITS,
        "signup_grant",
        "Welcome credits",
        reference_id=f"signup:{workspace_id}",
        created_by=created_by,
    )


def get_usage(db: Session, workspace_id: str) -> UsageResponse:
    wallet = ensure_wallet(db, workspace_id)
    subscription = db.scalar(select(Subscription).where(Subscription.workspace_id == workspace_id))
    plan = db.get(Plan, subscription.plan_id) if subscription else None
    period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    videos = int(
        db.scalar(
            select(func.count()).select_from(Video).where(
                Video.workspace_id == workspace_id,
                Video.created_at >= period_start,
            )
        )
        or 0
    )
    spent = int(
        db.scalar(
            select(func.coalesce(func.sum(CreditLedger.amount), 0)).where(
                CreditLedger.workspace_id == workspace_id,
                CreditLedger.entry_type == "reserve",
                CreditLedger.created_at >= period_start,
            )
        )
        or 0
    )
    return UsageResponse(
        workspace_id=workspace_id,
        balance=wallet.balance,
        reserved=wallet.reserved,
        available=wallet.balance,
        plan=PlanResponse.model_validate(plan) if plan else None,
        subscription_status=subscription.status if subscription else "none",
        videos_this_period=videos,
        credits_spent_this_period=abs(spent),
        estimated_next_video=estimate_credits(30, "1080p"),
    )


def job_credit_cost(job: Job) -> int:
    payload = job.input_data or {}
    if payload.get("credit_cost"):
        return int(payload["credit_cost"])
    return estimate_credits(payload.get("duration"), str(payload.get("resolution") or "1080p"))


def estimate_payload(duration: int, resolution: str) -> EstimateResponse:
    return EstimateResponse(credits=estimate_credits(duration, resolution), duration=duration, resolution=resolution)
