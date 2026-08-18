"""Registry for later AI video providers.

ShortGen still renders through MoneyPrinterTurboGenerationAdapter.
AI video/image providers only produce scene clips.
"""

from __future__ import annotations

import os

PROVIDERS = {
    "moneyprinterturbo": {
        "label": "ShortGen engine",
        "status": "active",
        "notes": "Existing MoviePy / stock / TTS pipeline.",
    },
    "replicate": {
        "label": "Replicate",
        "status": "active",
        "notes": "Official-model predictions for AI video and stills.",
    },
    "runway": {"label": "Runway", "status": "planned"},
    "kling": {"label": "Kling", "status": "planned"},
    "luma": {"label": "Luma", "status": "planned"},
}


def list_providers() -> list[dict]:
    enabled = (os.getenv("AI_VIDEO_ENABLED") or "true").strip().lower() not in {"0", "false", "no", "off"}
    items = []
    for key, value in PROVIDERS.items():
        item = {"id": key, **value}
        if key == "replicate" and not enabled:
            item["status"] = "disabled"
            item["notes"] = "AI video generation is temporarily unavailable."
        items.append(item)
    return items
