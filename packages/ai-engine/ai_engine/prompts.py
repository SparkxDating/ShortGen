"""Provider-ready visual prompts. Never send raw narration alone."""

from __future__ import annotations

DEFAULT_NEGATIVE = (
    "text, watermark, logo, subtitles, UI, distorted hands, deformed face, "
    "duplicate people, extra limbs, low quality, blurry, cartoon text"
)


def build_visual_prompt(
    *,
    narration: str,
    style: str = "cinematic",
    tone: str = "informative",
    camera_motion: str = "subtle push-in",
    visual_requirements: str = "",
    brand: str = "",
    location_continuity: str = "",
) -> str:
    subject = " ".join((narration or "").split())[:280]
    extra = " ".join((visual_requirements or "").split())[:180]
    continuity = " ".join((location_continuity or "").split())[:160]
    brand_bit = f" Brand mood: {brand}." if brand.strip() else ""
    cont_bit = f" Maintain continuity: {continuity}." if continuity else ""
    extra_bit = f" {extra}." if extra else ""
    motion = camera_motion.strip() or "subtle camera push-in"
    return (
        f"{style.capitalize()} {tone} documentary-style shot illustrating: {subject}. "
        f"{motion}, natural lighting, realistic human motion, premium technology aesthetic, "
        f"no text, no logos, no watermarks.{brand_bit}{cont_bit}{extra_bit}"
    ).strip()


def stock_query(narration: str, fallback: str = "cinematic b-roll") -> str:
    words = [token for token in (narration or "").replace(",", " ").split() if token.isalpha()]
    if not words:
        return fallback
    return " ".join(words[:6])[:80]
