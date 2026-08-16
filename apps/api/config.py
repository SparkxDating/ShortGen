"""SaaS API configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from apps.api.bootstrap import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name, "true" if default else "false").lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_expire_minutes: int
    jwt_algorithm: str
    cors_origins: tuple[str, ...]
    storage_provider: str
    storage_path: Path
    s3_bucket: str
    s3_region: str
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_public_base_url: str
    r2_account_id: str
    max_upload_bytes: int
    rate_limit_per_minute: int
    api_host: str
    api_port: int
    billing_provider: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    environment = _env("ENVIRONMENT", "development")
    jwt_secret = _env("JWT_SECRET")
    if not jwt_secret:
        if environment.lower() in {"prod", "production"}:
            raise RuntimeError("JWT_SECRET must be set in production")
        jwt_secret = "dev-only-change-me"

    origins_raw = _env(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
    )
    origins = tuple(item.strip() for item in origins_raw.split(",") if item.strip())

    storage_path = Path(_env("STORAGE_PATH", "./storage/saas")).expanduser()
    if not storage_path.is_absolute():
        storage_path = (REPO_ROOT / storage_path).resolve()

    database_url = _env("DATABASE_URL", f"sqlite:///{REPO_ROOT / 'saas.db'}")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return Settings(
        environment=environment,
        database_url=database_url,
        redis_url=_env("REDIS_URL", "redis://localhost:6379/0"),
        jwt_secret=jwt_secret,
        jwt_expire_minutes=_env_int("JWT_EXPIRE_MINUTES", 1440),
        jwt_algorithm=_env("JWT_ALGORITHM", "HS256"),
        cors_origins=origins or ("http://localhost:3000",),
        storage_provider=_env("STORAGE_PROVIDER", "local"),
        storage_path=storage_path,
        s3_bucket=_env("S3_BUCKET"),
        s3_region=_env("S3_REGION", "us-east-1"),
        s3_endpoint_url=_env("S3_ENDPOINT_URL"),
        s3_access_key=_env("S3_ACCESS_KEY"),
        s3_secret_key=_env("S3_SECRET_KEY"),
        s3_public_base_url=_env("S3_PUBLIC_BASE_URL"),
        r2_account_id=_env("R2_ACCOUNT_ID"),
        max_upload_bytes=_env_int("MAX_UPLOAD_BYTES", 100 * 1024 * 1024),
        rate_limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 120),
        api_host=_env("API_HOST", "0.0.0.0"),
        api_port=_env_int("API_PORT", 8000),
        billing_provider=_env("BILLING_PROVIDER", "local"),
        stripe_secret_key=_env("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=_env("STRIPE_WEBHOOK_SECRET"),
        razorpay_key_id=_env("RAZORPAY_KEY_ID"),
        razorpay_key_secret=_env("RAZORPAY_KEY_SECRET"),
        razorpay_webhook_secret=_env("RAZORPAY_WEBHOOK_SECRET"),
    )
