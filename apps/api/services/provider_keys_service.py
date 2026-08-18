"""Save LLM and stock keys into the existing config.toml.

This is not a second config system. The MoneyPrinterTurbo engine already
reads these fields from app.config. Empty submitted values are ignored so
a blank form cannot wipe a saved key.
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import Field

from apps.api.schemas.common import ORMModel

PROVIDERS = (
    {
        "id": "kimi",
        "label": "Kimi / Moonshot",
        "config_key": "moonshot_api_key",
        "llm_provider": "moonshot",
        "is_list": False,
    },
    {
        "id": "openai",
        "label": "OpenAI",
        "config_key": "openai_api_key",
        "llm_provider": "openai",
        "is_list": False,
    },
    {
        "id": "gemini",
        "label": "Google Gemini",
        "config_key": "gemini_api_key",
        "llm_provider": "gemini",
        "is_list": False,
    },
    {
        "id": "deepseek",
        "label": "DeepSeek",
        "config_key": "deepseek_api_key",
        "llm_provider": "deepseek",
        "is_list": False,
    },
    {
        "id": "pexels",
        "label": "Pexels",
        "config_key": "pexels_api_keys",
        "llm_provider": None,
        "is_list": True,
    },
)

class ProviderKeyStatus(ORMModel):
    id: str
    label: str
    configured: bool
    llm_provider: str | None = None


class ProviderKeysResponse(ORMModel):
    llm_provider: str
    keys: list[ProviderKeyStatus]


class ProviderKeysUpdate(ORMModel):
    llm_provider: str | None = None
    kimi: str = Field(default="", max_length=500)
    openai: str = Field(default="", max_length=500)
    gemini: str = Field(default="", max_length=500)
    deepseek: str = Field(default="", max_length=500)
    pexels: str = Field(default="", max_length=500)


def _app_config() -> dict[str, Any]:
    from app.config import config

    return config.app


def _key_configured(value: Any) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value or "").strip())


def status() -> ProviderKeysResponse:
    app = _app_config()
    keys = [
        ProviderKeyStatus(
            id=item["id"],
            label=item["label"],
            configured=_key_configured(app.get(item["config_key"])),
            llm_provider=item["llm_provider"],
        )
        for item in PROVIDERS
    ]
    return ProviderKeysResponse(
        llm_provider=str(app.get("llm_provider") or "moonshot"),
        keys=keys,
    )


def update(payload: ProviderKeysUpdate) -> ProviderKeysResponse:
    from app.config import config
    from app.config.config import save_config

    app = config.app
    submitted = {
        "kimi": payload.kimi,
        "openai": payload.openai,
        "gemini": payload.gemini,
        "deepseek": payload.deepseek,
        "pexels": payload.pexels,
    }
    for item in PROVIDERS:
        raw = (submitted.get(item["id"]) or "").strip()
        if not raw:
            continue
        if item["is_list"]:
            app[item["config_key"]] = [raw]
        else:
            app[item["config_key"]] = raw
        if item["config_key"] == "openai_api_key":
            os.environ["OPENAI_API_KEY"] = raw
        if item["config_key"] == "gemini_api_key":
            os.environ["GEMINI_API_KEY"] = raw

    if payload.llm_provider:
        match = next((item for item in PROVIDERS if item["llm_provider"] == payload.llm_provider), None)
        if match is None:
            from apps.api.services.errors import ServiceError

            raise ServiceError("llm_provider must be moonshot, openai, gemini, or deepseek")
        app["llm_provider"] = match["llm_provider"]

    save_config()
    return status()


def reload_from_disk() -> None:
    """Refresh in-memory keys so the worker sees Settings saves without a restart."""
    try:
        import toml
        from app.config import config
        from app.config.config import config_file
    except Exception:
        return
    try:
        data = toml.load(config_file)
    except Exception:
        return
    app = data.get("app") or {}
    for item in PROVIDERS:
        if item["config_key"] in app:
            config.app[item["config_key"]] = app[item["config_key"]]
    if app.get("llm_provider"):
        config.app["llm_provider"] = app["llm_provider"]
