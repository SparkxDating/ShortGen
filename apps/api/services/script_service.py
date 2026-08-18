"""Script preview uses the existing MoneyPrinterTurbo LLM path via the adapter."""

from __future__ import annotations

import logging
import re
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.models.workspace import WorkspaceRole
from apps.api.schemas.script import ScriptPreviewResponse
from apps.api.services import workspace_service
from apps.api.services.local_script import write_script
from apps.api.services.provider_keys_service import PROVIDERS, reload_from_disk
from video_engine.generation_adapter import MoneyPrinterTurboGenerationAdapter

logger = logging.getLogger("saas.script")

_FALLBACK_MODELS = {
    "gemini": (
        "gemini-3.1-flash-lite-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.7-flash",
        "gemini-3.1-pro-preview",
        "gemini-flash-latest",
    ),
    "openai": ("gpt-4o-mini", "gpt-4.1-mini"),
    "deepseek": ("deepseek-chat",),
    "moonshot": ("kimi-k2-turbo-preview", "moonshot-v1-8k"),
}


def preview_script(
    db: Session,
    user_id: str,
    workspace_id: str,
    topic: str,
    video_language: str,
    paragraph_number: int = 1,
) -> ScriptPreviewResponse:
    workspace_service.require_membership(db, workspace_id, user_id, WorkspaceRole.editor)
    try:
        reload_from_disk()
    except Exception:
        pass

    preferred, errors = _try_llm_script(topic, video_language, paragraph_number)
    if preferred:
        script, provider = preferred
        warning = ""
        if errors:
            warning = f"Used {provider} after {_summarize_errors(errors)}"
        return ScriptPreviewResponse(
            script=script,
            topic=topic,
            video_language=video_language,
            source="llm",
            provider=provider,
            warning=warning,
        )

    script = write_script(topic, video_language, vary=True)
    warning = "Used the local writer. " + (_summarize_errors(errors) if errors else "No working LLM key.")
    return ScriptPreviewResponse(
        script=script,
        topic=topic,
        video_language=video_language,
        source="local",
        warning=warning,
    )


def _try_llm_script(topic: str, video_language: str, paragraph_number: int):
    from app.config import config
    from app.services.task import generate_script

    app = config.app
    original_provider = str(app.get("llm_provider") or "moonshot")
    original_models = {
        f"{name}_model_name": app.get(f"{name}_model_name")
        for name in _FALLBACK_MODELS
    }
    errors: list[tuple[str, str]] = []
    adapter = MoneyPrinterTurboGenerationAdapter()
    params = adapter.build_params(
        {
            "topic": topic,
            "video_language": video_language,
            "paragraph_number": paragraph_number,
        }
    )
    import app.services.llm as llm_service

    previous_retries = getattr(llm_service, "_max_retries", 5)
    llm_service._max_retries = 1
    try:
        for provider in _provider_order(original_provider):
            if not _provider_has_key(provider):
                continue
            configured = str(app.get(f"{provider}_model_name") or "").strip()
            models = ((configured,) if configured else ()) + _FALLBACK_MODELS.get(provider, ())
            seen: set[str] = set()
            for model in models:
                model = (model or "").strip()
                if not model or model in seen:
                    continue
                seen.add(model)
                app["llm_provider"] = provider
                app[f"{provider}_model_name"] = model
                try:
                    script = generate_script(f"preview-{uuid4().hex}", params)
                    if script and not str(script).startswith("Error"):
                        try:
                            from app.config.config import save_config

                            save_config()
                        except Exception:
                            logger.warning("could not persist working llm_provider=%s", provider)
                        return (script, provider), errors
                    errors.append((provider, _clean_error(script or "empty response")))
                except Exception as exc:
                    errors.append((provider, _clean_error(str(exc))))
                    logger.warning("LLM preview failed provider=%s error=%s", provider, errors[-1][1])
    finally:
        llm_service._max_retries = previous_retries

    app["llm_provider"] = original_provider
    for key, value in original_models.items():
        if value is None:
            app.pop(key, None)
        else:
            app[key] = value
    return None, errors


def _provider_order(preferred: str) -> list[str]:
    names = [preferred] if preferred else []
    for item in PROVIDERS:
        name = item.get("llm_provider")
        if name and name not in names:
            names.append(name)
    return names


def _provider_has_key(provider: str) -> bool:
    from app.config import config

    value = config.app.get(f"{provider}_api_key")
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value or "").strip())


def _clean_error(message: str) -> str:
    text = re.sub(r"(sk-[A-Za-z0-9_-]+|AIza[A-Za-z0-9_-]+)", "[redacted]", str(message or ""))
    text = re.sub(r"\s+", " ", text).strip()
    lowered = text.lower()
    if "401" in text or "invalid authentication" in lowered:
        return "invalid API key"
    if "429" in text or "insufficient_quota" in lowered or "no credits" in lowered or "resource_exhausted" in lowered:
        return "no credits or quota left"
    if "402" in text or "insufficient balance" in lowered:
        return "insufficient balance"
    if "503" in text or "high demand" in lowered:
        return "temporarily busy"
    if "404" in text or "not found" in lowered or "no longer available" in lowered:
        return "model not available"
    if "no module named 'google'" in lowered:
        return "Gemini SDK missing"
    return text[:120]


def _summarize_errors(errors: list[tuple[str, str]]) -> str:
    if not errors:
        return ""
    seen: set[tuple[str, str]] = set()
    parts: list[str] = []
    for name, reason in errors:
        item = (name, reason)
        if item in seen:
            continue
        seen.add(item)
        parts.append(f"{name}: {reason}")
    return "; ".join(parts)


def _llm_configured() -> bool:
    try:
        reload_from_disk()
    except Exception:
        pass
    from app.config import config

    provider = str(config.app.get("llm_provider") or "")
    if provider and _provider_has_key(provider):
        return True
    return any(
        item.get("llm_provider") and _provider_has_key(item["llm_provider"])
        for item in PROVIDERS
    )
