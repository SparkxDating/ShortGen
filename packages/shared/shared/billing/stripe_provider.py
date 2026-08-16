"""Stripe Checkout + Customer Portal. Optional — local provider is the default."""

from __future__ import annotations

import json
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
        session = self._stripe.checkout.Session.create(
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={**metadata, "workspace_id": workspace_id, "kind": kind, "item_id": item_id},
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "product_data": {"name": product_name},
                    },
                }
            ],
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
        data = event
        event_type = data.get("type") if isinstance(data, dict) else data["type"]
        obj: dict[str, Any]
        if isinstance(data, dict):
            obj = data.get("data", {}).get("object", {})
            event_id = data.get("id", "")
        else:
            obj = data["data"]["object"]
            event_id = data["id"]
        metadata = obj.get("metadata") or {}
        return WebhookResult(
            event_id=str(event_id),
            event_type=str(event_type),
            workspace_id=metadata.get("workspace_id"),
            kind=metadata.get("kind"),
            item_id=metadata.get("item_id"),
            payload=obj,
        )
