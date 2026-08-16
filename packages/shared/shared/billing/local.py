"""Local billing provider. Completes purchases immediately without a card network."""

from __future__ import annotations

from uuid import uuid4

from shared.billing.interface import CheckoutSession, WebhookResult


class LocalBillingProvider:
    name = "local"

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
        return CheckoutSession(
            provider="local",
            completed=True,
            checkout_url=None,
            session_id=f"local_{uuid4().hex}",
            message=f"Added {credits} credits locally for {product_name}.",
        )

    def create_portal(self, customer_id: str, return_url: str) -> str:
        return return_url

    def parse_webhook(self, payload: bytes, headers: dict[str, str]) -> WebhookResult:
        raise RuntimeError("the local billing provider does not receive webhooks")
