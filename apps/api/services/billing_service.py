from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.models.billing import BillingEvent, CreditPack, Plan, Subscription
from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.billing import (
    CheckoutResponse,
    CreditPackResponse,
    LedgerEntryResponse,
    PlanResponse,
)
from apps.api.services import credit_service, workspace_service
from apps.api.services.errors import ForbiddenError, NotFoundError, ServiceError
from shared.billing.factory import create_billing_provider


def get_provider():
    settings = get_settings()
    return create_billing_provider(
        settings.billing_provider,
        stripe_secret_key=settings.stripe_secret_key,
        stripe_webhook_secret=settings.stripe_webhook_secret,
        razorpay_key_id=settings.razorpay_key_id,
        razorpay_key_secret=settings.razorpay_key_secret,
        razorpay_webhook_secret=settings.razorpay_webhook_secret,
    )


def list_plans(db: Session) -> list[PlanResponse]:
    plans = list(db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_cents.asc())).all())
    return [PlanResponse.model_validate(plan) for plan in plans]


def list_packs(db: Session) -> list[CreditPackResponse]:
    packs = list(
        db.scalars(select(CreditPack).where(CreditPack.is_active.is_(True)).order_by(CreditPack.credits.asc())).all()
    )
    return [CreditPackResponse.model_validate(pack) for pack in packs]


def list_ledger(db: Session, workspace_id: str, user_id: str) -> list[LedgerEntryResponse]:
    workspace_service.require_membership(db, workspace_id, user_id)
    from apps.api.models.billing import CreditLedger

    rows = list(
        db.scalars(
            select(CreditLedger)
            .where(CreditLedger.workspace_id == workspace_id)
            .order_by(CreditLedger.created_at.desc())
            .limit(100)
        ).all()
    )
    return [LedgerEntryResponse.model_validate(row) for row in rows]


def checkout(
    db: Session,
    user_id: str,
    workspace_id: str,
    kind: str,
    item_id: str,
    success_url: str,
    cancel_url: str,
) -> CheckoutResponse:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.admin)
    if kind == "pack":
        item = db.get(CreditPack, item_id) or db.scalar(select(CreditPack).where(CreditPack.slug == item_id))
        if item is None or not item.is_active:
            raise NotFoundError("credit pack not found")
        credits = item.credits
        amount = item.price_cents
        name = item.name
        resolved_id = item.id
    elif kind == "plan":
        item = db.get(Plan, item_id) or db.scalar(select(Plan).where(Plan.slug == item_id))
        if item is None or not item.is_active:
            raise NotFoundError("plan not found")
        credits = item.monthly_credits
        amount = item.price_cents
        name = item.name
        resolved_id = item.id
    else:
        raise ServiceError("kind must be pack or plan")

    provider = get_provider()
    session = provider.create_checkout(
        workspace_id=workspace_id,
        kind=kind,
        item_id=resolved_id,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"workspace_id": workspace_id, "kind": kind, "item_id": resolved_id},
        amount_cents=amount,
        credits=credits,
        product_name=name,
    )
    if session.completed:
        _fulfill(db, workspace_id, kind, resolved_id, user_id, provider.name, session.session_id or "local")
        db.commit()
    return CheckoutResponse(
        provider=session.provider,
        completed=session.completed,
        checkout_url=session.checkout_url,
        message=session.message,
    )


def _fulfill(
    db: Session,
    workspace_id: str,
    kind: str,
    item_id: str,
    user_id: str | None,
    provider: str,
    event_id: str,
) -> None:
    if db.scalar(select(BillingEvent.id).where(BillingEvent.event_id == event_id)):
        return
    db.add(
        BillingEvent(
            provider=provider,
            event_id=event_id,
            event_type=f"{kind}.purchased",
            payload={"workspace_id": workspace_id, "item_id": item_id},
        )
    )
    if kind == "pack":
        pack = db.get(CreditPack, item_id)
        if pack is None:
            raise NotFoundError("credit pack not found")
        credit_service.grant(
            db,
            workspace_id,
            pack.credits,
            "pack_purchase",
            f"Purchased {pack.name}",
            reference_id=event_id,
            created_by=user_id,
        )
        return
    plan = db.get(Plan, item_id)
    if plan is None:
        raise NotFoundError("plan not found")
    subscription = db.scalar(select(Subscription).where(Subscription.workspace_id == workspace_id))
    if subscription is None:
        subscription = Subscription(workspace_id=workspace_id, plan_id=plan.id, provider=provider)
        db.add(subscription)
    else:
        subscription.plan_id = plan.id
        subscription.provider = provider
        subscription.status = "active"
    subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    credit_service.grant(
        db,
        workspace_id,
        plan.monthly_credits,
        "subscription_grant",
        f"{plan.name} monthly credits",
        reference_id=event_id,
        created_by=user_id,
    )


def handle_webhook(db: Session, provider_name: str, payload: bytes, headers: dict[str, str]) -> dict[str, str]:
    provider = get_provider()
    if provider.name != provider_name:
        raise ServiceError("webhook provider does not match BILLING_PROVIDER")
    result = provider.parse_webhook(payload, headers)
    if result.workspace_id and result.kind and result.item_id:
        _fulfill(
            db,
            result.workspace_id,
            result.kind,
            result.item_id,
            None,
            provider_name,
            result.event_id,
        )
        db.commit()
    return {"status": "ok", "event_id": result.event_id}


def create_portal(db: Session, workspace_id: str, user_id: str, return_url: str) -> str:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.admin)
    subscription = db.scalar(select(Subscription).where(Subscription.workspace_id == workspace_id))
    customer_id = subscription.provider_customer_id if subscription else ""
    if not customer_id:
        raise ForbiddenError("no billing customer is linked yet")
    return get_provider().create_portal(customer_id, return_url)


def dev_grant(db: Session, workspace_id: str, user_id: str, credits: int, description: str) -> None:
    settings = get_settings()
    if settings.is_production:
        raise ForbiddenError("development grants are disabled in production")
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.admin)
    credit_service.grant(
        db,
        workspace_id,
        credits,
        "adjustment",
        description,
        reference_id=f"dev:{workspace_id}:{credits}:{datetime.now(timezone.utc).timestamp()}",
        created_by=user_id,
    )
    db.commit()
