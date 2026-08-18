from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from apps.api.bootstrap import ensure_sys_path

ensure_sys_path()

pytest.importorskip("sqlalchemy")
pytest.importorskip("jwt")
pytest.importorskip("bcrypt")

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod-32b")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "saas.db"
    storage_path = tmp_path / "storage"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("STORAGE_PATH", str(storage_path))
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("REDIS_URL", "memory://")
    monkeypatch.setenv("JWT_SECRET", "test-secret-do-not-use-in-prod-32b")

    from apps.api.config import get_settings
    from apps.api.database.session import init_db, reset_engine
    from apps.api.api.deps import get_queue, get_storage

    get_settings.cache_clear()
    get_queue.cache_clear()
    get_storage.cache_clear()
    reset_engine()
    init_db()

    from fastapi.testclient import TestClient
    from apps.api.main import app
    from shared.queue.factory import create_job_queue

    app.state.queue = create_job_queue(force_memory=True)
    app.state.storage = get_storage()

    with TestClient(app) as test_client:
        yield test_client

    reset_engine()
    get_settings.cache_clear()
    get_queue.cache_clear()
    get_storage.cache_clear()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(client, email: str, password: str = "password123", name: str = "Ada") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()
