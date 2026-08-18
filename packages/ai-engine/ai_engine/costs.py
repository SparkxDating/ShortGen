"""Central credit costs for AI visuals. Not commercial provider invoices."""

from __future__ import annotations

import json
import os


def _int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def video_base_credits() -> int:
    return _int("AI_VIDEO_BASE_CREDITS", 20)


def image_base_credits() -> int:
    return _int("AI_IMAGE_BASE_CREDITS", 3)


def model_costs() -> dict[str, int]:
    raw = (os.getenv("AI_VIDEO_MODEL_COSTS") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in data.items():
        try:
            out[str(key)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return out


def credits_for_video_model(model: str | None) -> int:
    if model and model in model_costs():
        return model_costs()[model]
    return video_base_credits()


def credits_for_visual(visual_type: str, model: str | None = None) -> int:
    kind = (visual_type or "").lower()
    if kind == "ai_video":
        return credits_for_video_model(model)
    if kind == "ai_image":
        return image_base_credits()
    return 0
