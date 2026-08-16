"""Structured logs without secrets."""

from __future__ import annotations

import logging
from typing import Any

_REDACT = {
    "password",
    "token",
    "jwt",
    "authorization",
    "api_key",
    "secret",
    "stripe",
    "razorpay",
    "webhook",
}


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    parts = [event]
    for key, value in fields.items():
        lowered = key.lower()
        if any(item in lowered for item in _REDACT):
            continue
        if value is None:
            continue
        parts.append(f"{key}={value}")
    logger.info(" ".join(parts))
