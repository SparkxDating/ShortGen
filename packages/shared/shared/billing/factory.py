from __future__ import annotations

from shared.billing.interface import BillingProvider
from shared.billing.local import LocalBillingProvider


def create_billing_provider(
    provider: str,
    *,
    stripe_secret_key: str = "",
    stripe_webhook_secret: str = "",
    razorpay_key_id: str = "",
    razorpay_key_secret: str = "",
    razorpay_webhook_secret: str = "",
) -> BillingProvider:
    name = (provider or "local").strip().lower()
    if name in {"local", "dev", "test"}:
        return LocalBillingProvider()
    if name == "stripe":
        from shared.billing.stripe_provider import StripeBillingProvider

        return StripeBillingProvider(stripe_secret_key, stripe_webhook_secret)
    if name == "razorpay":
        from shared.billing.razorpay_provider import RazorpayBillingProvider

        return RazorpayBillingProvider(razorpay_key_id, razorpay_key_secret, razorpay_webhook_secret)
    raise ValueError(f"unsupported billing provider: {provider}")
