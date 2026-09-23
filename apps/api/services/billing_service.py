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
from apps.api.services.errors import ConflictError, ForbiddenError, NotFoundError, ServiceError
from shared.billing.factory import create_billing_provider
from shared.billing.interface import WebhookResult


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
        if amount <= 0:
            raise ServiceError("the free plan does not require checkout")
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
        if provider.name != "local":
            raise ServiceError("only the local billing provider may grant credits without a webhook")
        _fulfill(db, workspace_id, kind, resolved_id, user_id, provider.name, session.session_id or "local")
        db.commit()
    settings = get_settings()
    return CheckoutResponse(
        provider=session.provider,
        completed=session.completed,
        checkout_url=session.checkout_url,
        session_id=session.session_id,
        razorpay_key_id=settings.razorpay_key_id if session.provider == "razorpay" else None,
        amount_cents=amount,
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
    subscription.status = "active"
    credit_service.grant(
        db,
        workspace_id,
        plan.monthly_credits,
        "subscription_grant",
        f"{plan.name} monthly credits",
        reference_id=event_id,
        created_by=user_id,
    )


_PAID_EVENTS = {
    "checkout.session.completed",
    "payment_intent.succeeded",
    "order.paid",
    "payment.captured",
}


def handle_webhook(db: Session, provider_name: str, payload: bytes, headers: dict[str, str]) -> dict[str, str]:
    from apps.api.observability import log_event
    import logging

    logger = logging.getLogger("saas.billing")
    provider = get_provider()
    if provider.name != provider_name:
        raise ServiceError("webhook provider does not match BILLING_PROVIDER")
    try:
        result = provider.parse_webhook(payload, headers)
    except Exception:
        logger.warning("billing webhook verification failed provider=%s", provider_name)
        raise ServiceError("invalid billing webhook", status_code=400)
    log_event(logger, "billing_webhook", provider=provider_name, event_type=result.event_type)
    apply_provider_event(db, provider_name, result)
    return {"status": "ok", "event_id": result.event_id}


def apply_provider_event(db: Session, provider_name: str, result: WebhookResult) -> None:
    """Apply a verified billing event. Subscription credits come from invoice.paid only."""
    event = result.event_type
    if event == "checkout.session.completed" and _is_subscription_checkout(result):
        _link_subscription(db, result, provider_name)
        db.commit()
        return
    if event == "invoice.paid":
        _grant_subscription_invoice(db, result, provider_name)
        db.commit()
        return
    if event in {"customer.subscription.updated", "customer.subscription.deleted"}:
        _sync_subscription_status(db, result)
        db.commit()
        return
    paid = event in _PAID_EVENTS or event.endswith(".purchased")
    if paid and result.workspace_id and result.kind and result.item_id:
        _fulfill(
            db,
            result.workspace_id,
            result.kind,
            result.item_id,
            None,
            provider_name,
            result.event_id,
        )
        _stamp_provider(db, result.workspace_id, provider_name, result)
        db.commit()


def _is_subscription_checkout(result: WebhookResult) -> bool:
    mode = result.mode or (result.payload or {}).get("mode")
    return mode == "subscription" or result.kind == "plan"


def _period_end(result: WebhookResult) -> datetime:
    if result.period_end:
        return datetime.fromtimestamp(int(result.period_end), tz=timezone.utc)
    return datetime.now(timezone.utc) + timedelta(days=30)


def _find_subscription(db: Session, result: WebhookResult) -> Subscription | None:
    if result.subscription_id:
        found = db.scalar(
            select(Subscription).where(Subscription.provider_subscription_id == result.subscription_id)
        )
        if found is not None:
            return found
    if result.workspace_id:
        return db.scalar(select(Subscription).where(Subscription.workspace_id == result.workspace_id))
    return None


def _resolve_plan(db: Session, item_id: str) -> Plan | None:
    return db.get(Plan, item_id) or db.scalar(select(Plan).where(Plan.slug == item_id))


def _stamp_provider(db: Session, workspace_id: str, provider: str, result: WebhookResult) -> None:
    subscription = db.scalar(select(Subscription).where(Subscription.workspace_id == workspace_id))
    if subscription is None:
        return
    subscription.provider = provider
    if result.customer_id:
        subscription.provider_customer_id = result.customer_id
    if result.subscription_id:
        subscription.provider_subscription_id = result.subscription_id
    if result.period_end:
        subscription.current_period_end = _period_end(result)


def _link_subscription(db: Session, result: WebhookResult, provider: str) -> None:
    if not result.workspace_id or not result.item_id:
        return
    plan = _resolve_plan(db, result.item_id)
    if plan is None:
        raise NotFoundError("plan not found")
    if db.scalar(select(BillingEvent.id).where(BillingEvent.event_id == result.event_id)) is None:
        db.add(
            BillingEvent(
                provider=provider,
                event_id=result.event_id,
                event_type="subscription.linked",
                payload={"workspace_id": result.workspace_id, "item_id": plan.id},
            )
        )
    subscription = db.scalar(select(Subscription).where(Subscription.workspace_id == result.workspace_id))
    if subscription is None:
        subscription = Subscription(workspace_id=result.workspace_id, plan_id=plan.id, provider=provider)
        db.add(subscription)
    subscription.plan_id = plan.id
    subscription.provider = provider
    subscription.status = "active"
    subscription.current_period_end = _period_end(result)
    db.flush()
    _stamp_provider(db, result.workspace_id, provider, result)


def _grant_subscription_invoice(db: Session, result: WebhookResult, provider: str) -> None:
    reason = str((result.payload or {}).get("billing_reason") or "")
    if reason and not reason.startswith("subscription"):
        return
    workspace_id = result.workspace_id
    item_id = result.item_id
    if not workspace_id or not item_id:
        existing = _find_subscription(db, result)
        if existing is not None:
            workspace_id = existing.workspace_id
            item_id = existing.plan_id
    if not workspace_id or not item_id:
        if result.subscription_id:
            raise ConflictError("subscription invoice is not linked to a workspace yet")
        return
    _fulfill(db, workspace_id, "plan", item_id, None, provider, result.event_id)
    _stamp_provider(db, workspace_id, provider, result)


def _sync_subscription_status(db: Session, result: WebhookResult) -> None:
    subscription = _find_subscription(db, result)
    if subscription is None:
        return
    if result.event_type == "customer.subscription.deleted":
        subscription.status = "canceled"
    else:
        subscription.status = str((result.payload or {}).get("status") or subscription.status)
    if result.customer_id:
        subscription.provider_customer_id = result.customer_id
    if result.subscription_id:
        subscription.provider_subscription_id = result.subscription_id
    if result.period_end:
        subscription.current_period_end = _period_end(result)


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
