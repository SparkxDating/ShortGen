"""Billing provider contract. Stripe and Razorpay are implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class CheckoutSession:
    provider: str
    completed: bool
    checkout_url: str | None = None
    session_id: str | None = None
    message: str = ""


@dataclass
class WebhookResult:
    event_id: str
    event_type: str
    workspace_id: str | None
    kind: str | None
    item_id: str | None
    payload: dict[str, Any]


class BillingProvider(Protocol):
    name: str

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
        ...

    def create_portal(self, customer_id: str, return_url: str) -> str:
        ...

    def parse_webhook(self, payload: bytes, headers: dict[str, str]) -> WebhookResult:
        ...
