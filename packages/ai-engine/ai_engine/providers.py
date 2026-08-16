"""Registry for later AI video providers.

Phase 4 initiation only. ShortGen still generates through
MoneyPrinterTurboGenerationAdapter. Do not add a second renderer here.
"""

from __future__ import annotations

PROVIDERS = {
    "moneyprinterturbo": {
        "label": "ShortGen engine",
        "status": "active",
        "notes": "Existing MoviePy / stock / TTS pipeline.",
    },
    "runway": {"label": "Runway", "status": "planned"},
    "kling": {"label": "Kling", "status": "planned"},
    "luma": {"label": "Luma", "status": "planned"},
}


def list_providers() -> list[dict]:
    return [{"id": key, **value} for key, value in PROVIDERS.items()]
