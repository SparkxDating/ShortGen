"""Razorpay order adapter. Optional — local provider is the default."""

from __future__ import annotations

import hashlib
import hmac
import json
from uuid import uuid4

from shared.billing.interface import CheckoutSession, WebhookResult


class RazorpayBillingProvider:
    name = "razorpay"

    def __init__(self, key_id: str, key_secret: str, webhook_secret: str = "") -> None:
        if not key_id or not key_secret:
            raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required")
        self.key_id = key_id
        self.key_secret = key_secret
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
        try:
            import razorpay
        except ImportError as exc:
            raise RuntimeError("Install razorpay to use BILLING_PROVIDER=razorpay") from exc
        client = razorpay.Client(auth=(self.key_id, self.key_secret))
        order = client.order.create(
            {
                "amount": amount_cents,
                "currency": "USD",
                "notes": {
                    "workspace_id": workspace_id,
                    "kind": kind,
                    "item_id": item_id,
                    "credits": str(credits),
                    "product_name": product_name,
                },
            }
        )
        return CheckoutSession(
            provider="razorpay",
            completed=False,
            checkout_url=None,
            session_id=order.get("id") or f"rzp_{uuid4().hex}",
            message="Complete payment with Razorpay Checkout using the order id. Do not treat the app success URL as paid.",
        )

    def create_portal(self, customer_id: str, return_url: str) -> str:
        return return_url

    def parse_webhook(self, payload: bytes, headers: dict[str, str]) -> WebhookResult:
        if not self.webhook_secret:
            raise RuntimeError("RAZORPAY_WEBHOOK_SECRET is required to verify Razorpay webhooks")
        signature = headers.get("x-razorpay-signature") or ""
        if not signature:
            raise RuntimeError("missing X-Razorpay-Signature header")
        digest = hmac.new(self.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, signature):
            raise RuntimeError("invalid Razorpay webhook signature")
        data = json.loads(payload.decode("utf-8"))
        entity = (((data.get("payload") or {}).get("order") or {}).get("entity")) or {}
        notes = entity.get("notes") or {}
        return WebhookResult(
            event_id=str(data.get("event") or "") + ":" + str(entity.get("id") or uuid4().hex),
            event_type=str(data.get("event") or "order.paid"),
            workspace_id=notes.get("workspace_id"),
            kind=notes.get("kind"),
            item_id=notes.get("item_id"),
            payload=entity,
        )
