"""Seed plans and credit packs. Safe to run on every startup."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.models.billing import CreditPack, Plan

PLANS = [
    {
        "slug": "free",
        "name": "Free",
        "description": "Enough credits to try the studio.",
        "monthly_credits": 100,
        "price_cents": 0,
    },
    {
        "slug": "starter",
        "name": "Starter",
        "description": "For a single creator shipping weekly.",
        "monthly_credits": 500,
        "price_cents": 1900,
    },
    {
        "slug": "pro",
        "name": "Pro",
        "description": "For a small team with daily generation.",
        "monthly_credits": 2000,
        "price_cents": 4900,
    },
]

PACKS = [
    {"slug": "pack-100", "name": "100 credits", "credits": 100, "price_cents": 900},
    {"slug": "pack-500", "name": "500 credits", "credits": 500, "price_cents": 2900},
    {"slug": "pack-2000", "name": "2,000 credits", "credits": 2000, "price_cents": 7900},
]


def seed_billing_catalog(db: Session) -> None:
    for item in PLANS:
        existing = db.scalar(select(Plan).where(Plan.slug == item["slug"]))
        if existing:
            continue
        db.add(Plan(**item, currency="usd", is_active=True))
    for item in PACKS:
        existing = db.scalar(select(CreditPack).where(CreditPack.slug == item["slug"]))
        if existing:
            continue
        db.add(CreditPack(**item, currency="usd", is_active=True))
    db.commit()
