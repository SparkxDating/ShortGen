from __future__ import annotations

import threading

import pytest

from test.saas.conftest import auth_header, register


def test_production_rejects_local_billing(monkeypatch):
    from apps.api.config import get_settings, validate_settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32)
    monkeypatch.setenv("BILLING_PROVIDER", "local")
    monkeypatch.setenv("CORS_ORIGINS", "https://shortgen.example")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="BILLING_PROVIDER=local"):
        validate_settings(get_settings())
    get_settings.cache_clear()


def test_production_rejects_weak_jwt(monkeypatch):
    from apps.api.config import Settings, validate_settings

    settings = Settings(
        environment="production",
        database_url="sqlite:///x",
        redis_url="memory://",
        jwt_secret="dev-only-change-me",
        jwt_expire_minutes=60,
        jwt_algorithm="HS256",
        cors_origins=("https://app.example",),
        storage_provider="local",
        storage_path=".",
        s3_bucket="",
        s3_region="us-east-1",
        s3_endpoint_url="",
        s3_access_key="",
        s3_secret_key="",
        s3_public_base_url="",
        r2_account_id="",
        max_upload_bytes=1,
        rate_limit_per_minute=10,
        api_host="0.0.0.0",
        api_port=8000,
        billing_provider="stripe",
        stripe_secret_key="sk",
        stripe_webhook_secret="whsec",
        razorpay_key_id="",
        razorpay_key_secret="",
        razorpay_webhook_secret="",
        rate_limit_backend="memory",
        job_stale_seconds=180,
        job_max_retries=3,
        signed_url_ttl=60,
        auto_create_schema=False,
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_settings(settings)


def test_idempotent_video_create(client):
    user = register(client, "idem@example.com")
    headers = auth_header(user["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.get("/api/v1/projects", params={"workspace_id": workspace["id"]}, headers=headers).json()[0]
    payload = {
        "workspace_id": workspace["id"],
        "project_id": project["id"],
        "title": "Once",
        "topic": "Once",
        "duration": 30,
        "resolution": "720p",
    }
    first = client.post("/api/v1/videos", json=payload, headers={**headers, "Idempotency-Key": "abc-1"})
    second = client.post("/api/v1/videos", json=payload, headers={**headers, "Idempotency-Key": "abc-1"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_cross_workspace_template_and_billing(client):
    alice = register(client, "iso-a@example.com")
    bob = register(client, "iso-b@example.com")
    alice_h = auth_header(alice["access_token"])
    bob_h = auth_header(bob["access_token"])
    alice_ws = client.get("/api/v1/workspaces", headers=alice_h).json()[0]
    created = client.post(
        "/api/v1/templates",
        json={"workspace_id": alice_ws["id"], "name": "Private", "description": "", "config": {}},
        headers=alice_h,
    )
    assert created.status_code == 201
    hidden = client.get(f"/api/v1/templates/{created.json()['id']}", headers=bob_h)
    assert hidden.status_code == 404
    usage = client.get("/api/v1/billing/usage", params={"workspace_id": alice_ws["id"]}, headers=bob_h)
    assert usage.status_code == 404
    ledger = client.get("/api/v1/billing/ledger", params={"workspace_id": alice_ws["id"]}, headers=bob_h)
    assert ledger.status_code == 404


def test_unsigned_stripe_webhook_rejected(client):
    response = client.post("/api/v1/billing/webhooks/stripe", content=b'{"type":"checkout.session.completed"}')
    assert response.status_code in {400, 500}


def test_wallet_concurrency_does_not_overspend(tmp_path, monkeypatch):
    from apps.api.config import get_settings
    from apps.api.database.session import SessionLocal, init_db, reset_engine
    from apps.api.models.billing import CreditWallet
    from apps.api.services import credit_service

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'wallet.db'}")
    get_settings.cache_clear()
    reset_engine()
    init_db()
    db = SessionLocal()
    workspace_id = "ws-lock"
    wallet = CreditWallet(workspace_id=workspace_id, balance=100, reserved=0)
    db.add(wallet)
    db.commit()
    db.close()

    results: list[str] = []

    def attempt(job_id: str) -> None:
        session = SessionLocal()
        try:
            credit_service.reserve(session, workspace_id, job_id, 80)
            session.commit()
            results.append("ok")
        except credit_service.PaymentRequiredError:
            session.rollback()
            results.append("deny")
        finally:
            session.close()

    t1 = threading.Thread(target=attempt, args=("job-a",))
    t2 = threading.Thread(target=attempt, args=("job-b",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert results.count("ok") == 1
    assert results.count("deny") == 1
    db = SessionLocal()
    wallet = credit_service.ensure_wallet(db, workspace_id)
    assert wallet.balance >= 0
    assert wallet.balance == 20
    assert wallet.reserved == 80
    db.close()
    reset_engine()


def test_duplicate_refund_is_noop(client):
    from apps.api.database.session import SessionLocal
    from apps.api.services import credit_service

    user = register(client, "refund2@example.com")
    headers = auth_header(user["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.get("/api/v1/projects", params={"workspace_id": workspace["id"]}, headers=headers).json()[0]
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "R",
            "topic": "R",
            "duration": 30,
            "resolution": "720p",
        },
        headers=headers,
    ).json()
    job_id = video["latest_job"]["id"]
    db = SessionLocal()
    credit_service.refund(db, workspace["id"], job_id, retry_count=0)
    first = credit_service.ensure_wallet(db, workspace["id"]).balance
    credit_service.refund(db, workspace["id"], job_id, retry_count=0)
    second = credit_service.ensure_wallet(db, workspace["id"]).balance
    db.commit()
    db.close()
    assert first == second


def test_stale_job_recovery_refunds_once(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from apps.api.config import get_settings
    from apps.api.database.session import SessionLocal, init_db, reset_engine
    from apps.api.models.job import Job, JobStatus
    from apps.api.models.user import User
    from apps.api.models.video import Video, VideoStatus
    from apps.api.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
    from apps.api.services import credit_service, job_recovery
    from apps.api.services.billing_catalog import seed_billing_catalog
    from shared.queue.factory import create_job_queue

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'stale.db'}")
    get_settings.cache_clear()
    reset_engine()
    init_db()
    db = SessionLocal()
    seed_billing_catalog(db)
    user = User(email="stale@example.com", name="S", password_hash="x")
    db.add(user)
    db.flush()
    workspace = Workspace(name="W", slug="w-stale", owner_id=user.id)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.owner.value))
    credit_service.provision_workspace(db, workspace.id, user.id)
    from apps.api.models.project import Project

    project = Project(workspace_id=workspace.id, name="P", created_by=user.id)
    db.add(project)
    db.flush()
    video = Video(
        workspace_id=workspace.id,
        project_id=project.id,
        title="V",
        status=VideoStatus.processing.value,
        created_by=user.id,
    )
    db.add(video)
    db.flush()
    job = Job(
        workspace_id=workspace.id,
        video_id=video.id,
        status=JobStatus.RUNNING.value,
        current_stage="RENDERING",
        input_data={"credit_cost": 10, "duration": 15, "resolution": "720p"},
        heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        retry_count=99,
    )
    db.add(job)
    db.flush()
    credit_service.reserve(db, workspace.id, job.id, 10, retry_count=99)
    db.commit()
    before = credit_service.ensure_wallet(db, workspace.id).balance
    recovered = job_recovery.recover_stale_jobs(db, create_job_queue(force_memory=True))
    assert recovered == 1
    db.refresh(job)
    assert job.status == JobStatus.FAILED.value
    after = credit_service.ensure_wallet(db, workspace.id).balance
    assert after == before + 10
    credit_service.refund(db, workspace.id, job.id, retry_count=99)
    assert credit_service.ensure_wallet(db, workspace.id).balance == after
    db.close()
    reset_engine()


def test_rate_limiter_memory_blocks():
    from shared.security.rate_limit import RateLimiter

    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("ip")
    assert limiter.allow("ip")
    assert limiter.allow("ip") is False
