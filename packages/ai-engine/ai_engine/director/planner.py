"""Build a validated VideoPlan. Never crash on malformed LLM JSON."""

from __future__ import annotations

import json
import re
from uuid import uuid4

from ai_engine.director.schema import ScenePlan, VideoPlan
from ai_engine.prompts import build_visual_prompt, stock_query

_FICTION = ("alien", "dragon", "superhero", "fantasy", "magic", "spaceship", "cyberpunk", "fictional")
_INFO = ("chart", "graph", "infographic", "statistic", "percent", "number", "data")
_REAL = ("history", "historical", "news", "hospital", "city", "india", "government", "documentary")


def plan_video(
    *,
    topic: str,
    script: str,
    duration: int = 30,
    language: str = "en-US",
    aspect_ratio: str = "9:16",
    resolution: str = "1080p",
    style: str = "cinematic",
    tone: str = "informative",
    target_platform: str = "short",
    visual_mode: str = "auto",
    raw_json: str | None = None,
    asset_ids: list[str] | None = None,
) -> VideoPlan:
    repaired = repair_plan_json(raw_json) if raw_json else None
    if repaired is not None:
        return _apply_mode(repaired, visual_mode, asset_ids or [])
    return _from_script(
        topic=topic,
        script=script,
        duration=duration,
        language=language,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        style=style,
        tone=tone,
        target_platform=target_platform,
        visual_mode=visual_mode,
        asset_ids=asset_ids or [],
    )


def repair_plan_json(raw: str | None) -> VideoPlan | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    for candidate in (text, text.replace("'", '"')):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        try:
            return VideoPlan.model_validate(_normalize_payload(data))
        except Exception:
            continue
    return None


def _normalize_payload(data: dict) -> dict:
    scenes = data.get("scenes") or []
    normalized = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        scene = dict(scene)
        scene.setdefault("id", f"scene-{index}")
        scene.setdefault("order", index)
        scene.setdefault("narration", scene.get("text") or scene.get("voiceover") or "Continue the story.")
        scene.setdefault("duration", 5)
        normalized.append(scene)
    data = dict(data)
    data["scenes"] = normalized or [
        {
            "id": "scene-1",
            "order": 1,
            "duration": 5,
            "narration": data.get("description") or data.get("title") or "Open on the topic.",
        }
    ]
    data.setdefault("title", data.get("hook") or "Untitled")
    return data


def _chunks(script: str, count: int) -> list[str]:
    text = " ".join((script or "").split())
    if not text:
        return ["Open on the topic and state the promise."]
    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [item.strip() for item in parts if item.strip()]
    if not parts:
        parts = [text]
    if len(parts) <= count:
        return parts
    group = max(1, len(parts) // count)
    out = []
    for index in range(0, len(parts), group):
        out.append(" ".join(parts[index : index + group]))
        if len(out) == count:
            if index + group < len(parts):
                out[-1] = out[-1] + " " + " ".join(parts[index + group :])
            break
    return out or [text]


def _choose_type(text: str, visual_mode: str, has_assets: bool, index: int, total: int) -> str:
    mode = (visual_mode or "auto").lower()
    if mode in {"stock", "stock_only"}:
        return "stock"
    if mode == "ai_video":
        return "ai_video"
    lowered = text.lower()
    if has_assets and index == 0:
        return "user_asset"
    if any(token in lowered for token in _INFO):
        return "ai_image"
    if any(token in lowered for token in _FICTION):
        return "ai_video"
    if any(token in lowered for token in _REAL):
        return "stock"
    if mode == "mixed":
        return ("ai_video", "stock", "ai_image")[index % 3]
    # AUTO: mostly stock, spend AI only where it helps
    if total >= 3 and index == 1:
        return "ai_video"
    if total >= 4 and index == total - 2:
        return "ai_image"
    return "stock"


def _from_script(
    *,
    topic: str,
    script: str,
    duration: int,
    language: str,
    aspect_ratio: str,
    resolution: str,
    style: str,
    tone: str,
    target_platform: str,
    visual_mode: str,
    asset_ids: list[str],
) -> VideoPlan:
    count = min(6, max(3, int(duration) // 6 or 3))
    bits = _chunks(script or topic, count)
    each = max(3.0, min(8.0, float(duration) / max(1, len(bits))))
    scenes: list[ScenePlan] = []
    location = topic.strip()
    for index, narration in enumerate(bits, start=1):
        visual = _choose_type(narration, visual_mode, bool(asset_ids), index - 1, len(bits))
        asset_id = asset_ids[0] if visual == "user_asset" and asset_ids else None
        scenes.append(
            ScenePlan(
                id=f"scene-{index}-{uuid4().hex[:6]}",
                order=index,
                duration=round(each, 2),
                narration=narration[:2000],
                visual_type=visual,  # type: ignore[arg-type]
                visual_prompt=build_visual_prompt(
                    narration=narration,
                    style=style,
                    tone=tone,
                    location_continuity=location,
                ),
                visual_query=stock_query(narration, topic),
                caption=narration[:180],
                camera_motion="subtle push-in" if visual == "ai_video" else "static",
                asset_id=asset_id,
                music_hint="cinematic",
            )
        )
    return VideoPlan(
        title=topic.strip()[:200] or "Untitled",
        hook=topic.strip()[:400],
        description=script[:2000],
        duration=int(duration),
        language=language,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        resolution=resolution,  # type: ignore[arg-type]
        style=style,
        tone=tone,
        target_platform=target_platform,
        visual_mode=visual_mode,  # type: ignore[arg-type]
        music_style="cinematic",
        scenes=scenes,
    )


def _apply_mode(plan: VideoPlan, visual_mode: str, asset_ids: list[str]) -> VideoPlan:
    mode = (visual_mode or plan.visual_mode or "auto").lower()
    data = plan.model_dump()
    data["visual_mode"] = mode if mode in {"auto", "stock", "ai_video", "mixed"} else "auto"
    for index, scene in enumerate(data["scenes"]):
        chosen = _choose_type(scene.get("narration") or "", data["visual_mode"], bool(asset_ids), index, len(data["scenes"]))
        scene["visual_type"] = chosen
        if chosen == "user_asset" and asset_ids:
            scene["asset_id"] = asset_ids[0]
    return VideoPlan.model_validate(data)
