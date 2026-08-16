from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from apps.api.schemas.common import ORMModel


class PlanResponse(ORMModel):
    id: str
    slug: str
    name: str
    description: str
    monthly_credits: int
    price_cents: int
    currency: str
    is_active: bool


class CreditPackResponse(ORMModel):
    id: str
    slug: str
    name: str
    credits: int
    price_cents: int
    currency: str
    is_active: bool


class LedgerEntryResponse(ORMModel):
    id: str
    workspace_id: str
    amount: int
    balance_after: int
    entry_type: str
    reference_type: str | None = None
    reference_id: str | None = None
    description: str
    created_at: datetime


class UsageResponse(ORMModel):
    workspace_id: str
    balance: int
    reserved: int
    available: int
    plan: PlanResponse | None = None
    subscription_status: str
    videos_this_period: int
    credits_spent_this_period: int
    estimated_next_video: int


class EstimateResponse(ORMModel):
    credits: int
    duration: int
    resolution: str


class CheckoutRequest(ORMModel):
    workspace_id: str
    kind: Literal["pack", "plan"]
    item_id: str


class CheckoutResponse(ORMModel):
    provider: str
    completed: bool
    checkout_url: str | None = None
    session_id: str | None = None
    razorpay_key_id: str | None = None
    amount_cents: int | None = None
    message: str


class DevGrantRequest(ORMModel):
    workspace_id: str
    credits: int = Field(gt=0, le=100000)
    description: str = "Development credit grant"


class BillingStatusResponse(ORMModel):
    provider: str
    live_ready: bool
    webhook_configured: bool
    environment: str
    message: str
