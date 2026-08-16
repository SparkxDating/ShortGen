from test.saas.conftest import auth_header, register


def _workspace(client, headers):
    return client.get("/api/v1/workspaces", headers=headers).json()[0]


def test_new_workspace_receives_welcome_credits(client):
    user = register(client, "credits@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    usage = client.get("/api/v1/billing/usage", params={"workspace_id": workspace["id"]}, headers=headers)
    assert usage.status_code == 200, usage.text
    assert usage.json()["available"] == 100
    assert usage.json()["plan"]["slug"] == "free"


def test_usage_is_workspace_isolated(client):
    alice = register(client, "alice-bill@example.com")
    bob = register(client, "bob-bill@example.com")
    alice_ws = _workspace(client, auth_header(alice["access_token"]))
    hidden = client.get(
        "/api/v1/billing/usage",
        params={"workspace_id": alice_ws["id"]},
        headers=auth_header(bob["access_token"]),
    )
    assert hidden.status_code == 404


def test_video_reserves_and_failure_refunds_credits(client):
    user = register(client, "spend@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Ads", "description": ""},
        headers=headers,
    ).json()
    before = client.get(
        "/api/v1/billing/usage", params={"workspace_id": workspace["id"]}, headers=headers
    ).json()["available"]
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Paid",
            "topic": "Paid topic",
            "duration": 30,
            "resolution": "1080p",
        },
        headers=headers,
    )
    assert video.status_code == 201, video.text
    cost = video.json()["latest_job"]["input_data"]["credit_cost"]
    assert cost > 0
    after_reserve = client.get(
        "/api/v1/billing/usage", params={"workspace_id": workspace["id"]}, headers=headers
    ).json()
    assert after_reserve["available"] == before - cost
    assert after_reserve["reserved"] == cost

    from apps.api.database.session import SessionLocal
    from apps.worker.runner import JobRunner
    from video_engine.generation_adapter import GenerationError

    class FailAdapter:
        def create_video(self, *args, **kwargs):
            raise GenerationError("mocked provider failure")

    db = SessionLocal()
    try:
        JobRunner(
            db,
            client.app.state.queue,
            client.app.state.storage,
            adapter_factory=lambda: FailAdapter(),
        ).process_job(video.json()["latest_job"]["id"])
    finally:
        db.close()

    refunded = client.get(
        "/api/v1/billing/usage", params={"workspace_id": workspace["id"]}, headers=headers
    ).json()
    assert refunded["available"] == before
    assert refunded["reserved"] == 0


def test_insufficient_credits_returns_402(client):
    user = register(client, "poor@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    # Burn the welcome balance with an oversized local grant reversal via many cheap? 
    # Directly set by purchasing nothing — create a video after zeroing via ledger grant of 0
    # Use a 300s 1080p video repeatedly until 402.
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Burn", "description": ""},
        headers=headers,
    ).json()
    created = 0
    last = None
    for _ in range(20):
        last = client.post(
            "/api/v1/videos",
            json={
                "workspace_id": workspace["id"],
                "project_id": project["id"],
                "title": f"Burn {created}",
                "topic": "Burn",
                "duration": 300,
                "resolution": "1080p",
            },
            headers=headers,
        )
        if last.status_code == 402:
            break
        created += 1
    assert last is not None
    assert last.status_code == 402
    assert "credits" in last.json()["detail"]


def test_local_pack_purchase_adds_credits(client):
    user = register(client, "buyer@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    packs = client.get("/api/v1/billing/packs", headers=headers)
    assert packs.status_code == 200
    pack = packs.json()[0]
    before = client.get(
        "/api/v1/billing/usage", params={"workspace_id": workspace["id"]}, headers=headers
    ).json()["available"]
    checkout = client.post(
        "/api/v1/billing/checkout",
        json={"workspace_id": workspace["id"], "kind": "pack", "item_id": pack["id"]},
        headers=headers,
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["completed"] is True
    after = client.get(
        "/api/v1/billing/usage", params={"workspace_id": workspace["id"]}, headers=headers
    ).json()["available"]
    assert after == before + pack["credits"]


def test_billing_status_reports_local_provider(client):
    user = register(client, "status@example.com")
    headers = auth_header(user["access_token"])
    status = client.get("/api/v1/billing/status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["provider"] == "local"
    assert body["live_ready"] is False
    assert "Local billing" in body["message"]


def test_director_plan_uses_existing_script_path(client):
    user = register(client, "director@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    providers = client.get("/api/v1/director/providers", headers=headers)
    assert providers.status_code == 200
    ids = {item["id"] for item in providers.json()}
    assert "moneyprinterturbo" in ids
    assert "runway" in ids
    planned = client.post(
        "/api/v1/director/plan",
        json={"workspace_id": workspace["id"], "topic": "Ocean facts", "video_language": "en-US"},
        headers=headers,
    )
    assert planned.status_code == 200, planned.text
    assert "Ocean facts" in planned.json()["plan"]
    assert planned.json()["renderer"] == "moneyprinterturbo"


def test_publish_rejects_unfinished_video(client):
    user = register(client, "publish@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Pub", "description": ""},
        headers=headers,
    ).json()
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Not ready",
            "topic": "Not ready",
        },
        headers=headers,
    ).json()
    published = client.post(f"/api/v1/videos/{video['id']}/publish", headers=headers)
    assert published.status_code == 400


def test_viewer_cannot_checkout(client):
    owner = register(client, "bill-owner@example.com")
    owner_headers = auth_header(owner["access_token"])
    workspace = _workspace(client, owner_headers)
    invite = client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "bill-view@example.com", "role": "viewer"},
        headers=owner_headers,
    ).json()
    viewer = register(client, "bill-view@example.com")
    client.post(
        "/api/v1/invites/accept",
        json={"token": invite["token"]},
        headers=auth_header(viewer["access_token"]),
    )
    packs = client.get("/api/v1/billing/packs", headers=owner_headers).json()
    denied = client.post(
        "/api/v1/billing/checkout",
        json={"workspace_id": workspace["id"], "kind": "pack", "item_id": packs[0]["id"]},
        headers=auth_header(viewer["access_token"]),
    )
    assert denied.status_code == 403
