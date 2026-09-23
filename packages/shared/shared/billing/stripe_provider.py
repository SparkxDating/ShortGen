"""Stripe Checkout + Customer Portal. Optional — local provider is the default."""

from __future__ import annotations

from typing import Any

from shared.billing.interface import CheckoutSession, WebhookResult


class StripeBillingProvider:
    name = "stripe"

    def __init__(self, secret_key: str, webhook_secret: str = "") -> None:
        if not secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY is required when BILLING_PROVIDER=stripe")
        try:
            import stripe
        except ImportError as exc:
            raise RuntimeError("Install stripe to use BILLING_PROVIDER=stripe") from exc
        self._stripe = stripe
        stripe.api_key = secret_key
        self.webhook_secret = webhook_secret

    def create_checkout(
        self,
        *,
        workspace_id: str,
        kind: str,
        item_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
        amount_cents: int,
        credits: int,
        product_name: str,
    ) -> CheckoutSession:
        shared = {**metadata, "workspace_id": workspace_id, "kind": kind, "item_id": item_id}
        price_data: dict[str, Any] = {
            "currency": "usd",
            "unit_amount": amount_cents,
            "product_data": {"name": product_name},
        }
        if kind == "plan":
            price_data["recurring"] = {"interval": "month"}
            session = self._stripe.checkout.Session.create(
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=workspace_id,
                metadata=shared,
                subscription_data={"metadata": shared},
                line_items=[{"quantity": 1, "price_data": price_data}],
            )
        else:
            session = self._stripe.checkout.Session.create(
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=workspace_id,
                customer_creation="always",
                metadata=shared,
                line_items=[{"quantity": 1, "price_data": price_data}],
            )
        return CheckoutSession(
            provider="stripe",
            completed=False,
            checkout_url=session.url,
            session_id=session.id,
            message="Redirect to Stripe Checkout",
        )

    def create_portal(self, customer_id: str, return_url: str) -> str:
        portal = self._stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
        return str(portal.url)

    def parse_webhook(self, payload: bytes, headers: dict[str, str]) -> WebhookResult:
        signature = headers.get("stripe-signature") or headers.get("Stripe-Signature") or ""
        if not self.webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is required to verify Stripe webhooks")
        if not signature:
            raise RuntimeError("missing Stripe-Signature header")
        event = self._stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
        data = event if isinstance(event, dict) else event.to_dict()
        event_type = str(data.get("type") or "")
        obj = (data.get("data") or {}).get("object") or {}
        if not isinstance(obj, dict):
            obj = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)
        metadata = _metadata_from(obj)
        customer = obj.get("customer")
        if isinstance(customer, dict):
            customer = customer.get("id")
        subscription = obj.get("subscription")
        if event_type.startswith("customer.subscription."):
            subscription = obj.get("id")
        if isinstance(subscription, dict):
            subscription = subscription.get("id")
        period_end = obj.get("current_period_end")
        lines = ((obj.get("lines") or {}).get("data") or [])
        if not period_end and lines:
            period_end = (lines[0].get("period") or {}).get("end")
        kind = metadata.get("kind")
        if event_type == "invoice.paid" and not kind and subscription:
            kind = "plan"
        return WebhookResult(
            event_id=str(data.get("id") or ""),
            event_type=event_type,
            workspace_id=metadata.get("workspace_id"),
            kind=kind,
            item_id=metadata.get("item_id"),
            payload=obj,
            customer_id=str(customer) if customer else None,
            subscription_id=str(subscription) if subscription else None,
            period_end=int(period_end) if period_end else None,
            mode=obj.get("mode"),
        )


def _metadata_from(obj: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        obj.get("metadata"),
        (obj.get("subscription_details") or {}).get("metadata"),
        ((obj.get("parent") or {}).get("subscription_details") or {}).get("metadata"),
    ]
    lines = ((obj.get("lines") or {}).get("data") or [])
    if lines:
        candidates.append(lines[0].get("metadata"))
    for raw in candidates:
        meta = dict(raw or {})
        if meta.get("workspace_id"):
            return meta
    return dict(obj.get("metadata") or {})
