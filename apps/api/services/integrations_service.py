"""Stripe and Upload-Post settings. Keys stay on this server, never in GitHub."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field

from apps.api.bootstrap import REPO_ROOT
from apps.api.schemas.common import ORMModel


class SocialSettings(ORMModel):
    configured: bool
    enabled: bool
    username_set: bool
    platforms: list[str]
    message: str


class SocialSettingsUpdate(ORMModel):
    api_key: str = Field(default="", max_length=500)
    username: str = Field(default="", max_length=120)
    enabled: bool | None = None
    platforms: list[str] = Field(default_factory=list)


class StripeSettings(ORMModel):
    provider: str
    live_ready: bool
    secret_set: bool
    webhook_set: bool
    webhook_url: str
    public_api_url: str
    message: str


class StripeSettingsUpdate(ORMModel):
    secret_key: str = Field(default="", max_length=200)
    webhook_secret: str = Field(default="", max_length=200)
    enable: bool = False


def _app():
    from app.config import config

    return config.app


def social_status() -> SocialSettings:
    app = _app()
    key = bool(str(app.get("upload_post_api_key") or "").strip())
    user = bool(str(app.get("upload_post_username") or "").strip())
    enabled = bool(app.get("upload_post_enabled"))
    platforms = list(app.get("upload_post_platforms") or ["tiktok", "instagram", "youtube"])
    configured = key and user and enabled
    if configured:
        message = "Upload-Post is on. Connect TikTok, Instagram, and YouTube in the Upload-Post dashboard for this username."
    elif key or user:
        message = "Key or username saved. Turn it on and save both fields to publish."
    else:
        message = "Create an account at https://upload-post.com, connect social accounts, then paste the API key and username here."
    return SocialSettings(
        configured=configured,
        enabled=enabled,
        username_set=user,
        platforms=platforms,
        message=message,
    )


def update_social(payload: SocialSettingsUpdate) -> SocialSettings:
    from app.config.config import save_config

    app = _app()
    if payload.api_key.strip():
        app["upload_post_api_key"] = payload.api_key.strip()
    if payload.username.strip():
        app["upload_post_username"] = payload.username.strip()
    if payload.enabled is not None:
        app["upload_post_enabled"] = bool(payload.enabled)
    allowed = {"tiktok", "instagram", "youtube", "youtube-shorts"}
    platforms = [item for item in payload.platforms if item in allowed]
    if platforms:
        app["upload_post_platforms"] = platforms
    save_config()
    _reload_social_from_disk()
    return social_status()


def public_api_url() -> str:
    return (os.getenv("PUBLIC_API_URL") or "http://127.0.0.1:8000").rstrip("/")


def stripe_webhook_url() -> str:
    return f"{public_api_url()}/api/v1/billing/webhooks/stripe"


def stripe_status() -> StripeSettings:
    from apps.api.config import get_settings

    settings = get_settings()
    secret = bool(settings.stripe_secret_key)
    webhook = bool(settings.stripe_webhook_secret)
    live = settings.billing_provider == "stripe" and secret and webhook
    hook = stripe_webhook_url()
    if live:
        message = f"Stripe is live. Credits are added only after a verified webhook at {hook}."
    elif settings.billing_provider == "local":
        message = "Local billing is on. Paste Stripe keys, add the webhook URL in Stripe, then enable to charge cards."
    else:
        message = "Stripe is selected but secret or webhook secret is missing."
    return StripeSettings(
        provider=settings.billing_provider,
        live_ready=live,
        secret_set=secret,
        webhook_set=webhook,
        webhook_url=hook,
        public_api_url=public_api_url(),
        message=message,
    )


def update_stripe(payload: StripeSettingsUpdate) -> StripeSettings:
    updates: dict[str, str] = {}
    if payload.secret_key.strip():
        updates["STRIPE_SECRET_KEY"] = payload.secret_key.strip()
        os.environ["STRIPE_SECRET_KEY"] = payload.secret_key.strip()
    if payload.webhook_secret.strip():
        updates["STRIPE_WEBHOOK_SECRET"] = payload.webhook_secret.strip()
        os.environ["STRIPE_WEBHOOK_SECRET"] = payload.webhook_secret.strip()
    if payload.enable:
        if not (os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_WEBHOOK_SECRET")):
            from apps.api.services.errors import ServiceError

            raise ServiceError("save both Stripe secret key and webhook secret before enabling")
        updates["BILLING_PROVIDER"] = "stripe"
        os.environ["BILLING_PROVIDER"] = "stripe"
    _write_env(updates)
    from apps.api.config import get_settings

    get_settings.cache_clear()
    return stripe_status()


def _write_env(updates: dict[str, str]) -> None:
    path = Path(REPO_ROOT) / ".env"
    existing: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            existing[name.strip()] = value
    existing.update(updates)
    lines = [f"{key}={value}" for key, value in existing.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _reload_social_from_disk() -> None:
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
    for key in (
        "upload_post_api_key",
        "upload_post_username",
        "upload_post_enabled",
        "upload_post_platforms",
        "upload_post_auto_upload",
        "upload_post_youtube_privacy_status",
    ):
        if key in app:
            config.app[key] = app[key]
