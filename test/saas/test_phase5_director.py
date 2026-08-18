from ai_engine.director.planner import plan_video, repair_plan_json
from ai_engine.router import AIProviderRouter, ProviderNotAllowed
from ai_engine.video.mock import MockAIVideoProvider
from ai_engine.costs import credits_for_visual
from test.saas.conftest import auth_header, register


def _workspace(client, headers):
    return client.get("/api/v1/workspaces", headers=headers).json()[0]


def test_director_json_and_malformed_repair():
    plan = plan_video(topic="India AI", script="Hospitals use AI. Charts show growth. A fictional robot helps.", duration=30)
    assert plan.scenes
    assert all(scene.visual_prompt for scene in plan.scenes)
    repaired = repair_plan_json('{"title":"X","scenes":[{"narration":"Hello","duration":4}]}')
    assert repaired is not None
    assert repaired.scenes[0].narration == "Hello"
    assert repair_plan_json("not json") is None


def test_stock_only_keeps_stock_types():
    plan = plan_video(topic="News", script="A real hospital in India. Historical footage.", duration=24, visual_mode="stock")
    assert all(scene.visual_type == "stock" for scene in plan.scenes)


def test_ai_video_only_mode():
    plan = plan_video(topic="Fantasy", script="A dragon flies over a city.", duration=18, visual_mode="ai_video")
    assert all(scene.visual_type == "ai_video" for scene in plan.scenes)


def test_provider_selection_rejects_arbitrary():
    router = AIProviderRouter(environment="test")
    assert router.select_video_provider().name == "mock"
    try:
        router.select_video_provider("https://evil.example")
        assert False, "should reject"
    except ProviderNotAllowed:
        pass


def test_mock_provider_is_not_production():
    router = AIProviderRouter(environment="production", video_provider="mock", video_enabled=True)
    try:
        router.select_video_provider("mock")
        assert False, "mock blocked in production"
    except ProviderNotAllowed:
        pass


def test_mock_video_and_failure():
    ok = MockAIVideoProvider()
    handle = ok.create_generation(prompt="x", aspect_ratio="9:16", duration=5)
    assert handle.status.value == "COMPLETED"
    fail = MockAIVideoProvider(fail=True)
    bad = fail.create_generation(prompt="x", aspect_ratio="9:16", duration=5)
    assert bad.status.value == "FAILED"


def test_credit_costs():
    assert credits_for_visual("stock") == 0
    assert credits_for_visual("ai_video") >= 1
    assert credits_for_visual("ai_image") >= 1


def test_capabilities_and_structured_plan(client):
    user = register(client, "phase5@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    caps = client.get("/api/v1/ai/capabilities", headers=headers)
    assert caps.status_code == 200, caps.text
    planned = client.post(
        "/api/v1/director/plan",
        json={
            "workspace_id": workspace["id"],
            "topic": "Ocean facts",
            "video_language": "en-US",
            "visual_mode": "auto",
            "duration": 30,
            "aspect_ratio": "9:16",
        },
        headers=headers,
    )
    assert planned.status_code == 200, planned.text
    body = planned.json()
    assert "Ocean facts" in body["plan"]
    assert body["renderer"] == "moneyprinterturbo"
    assert body["video_plan"]["scenes"]
    assert body["video_plan"]["scenes"][0]["visual_prompt"]


def test_scene_endpoints_and_cross_workspace(client):
    alice = register(client, "alice-p5@example.com")
    bob = register(client, "bob-p5@example.com")
    a_headers = auth_header(alice["access_token"])
    b_headers = auth_header(bob["access_token"])
    workspace = _workspace(client, a_headers)
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "P5", "description": ""},
        headers=a_headers,
    ).json()
    created = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Mixed",
            "topic": "India AI revolution",
            "visual_mode": "mixed",
            "director_plan": {
                "title": "India AI",
                "duration": 30,
                "language": "en-US",
                "aspect_ratio": "9:16",
                "resolution": "1080p",
                "visual_mode": "mixed",
                "scenes": [
                    {
                        "id": "s1",
                        "order": 1,
                        "duration": 5,
                        "narration": "Hospitals adopt AI.",
                        "visual_type": "stock",
                        "visual_prompt": "hospital",
                        "visual_query": "hospital",
                    }
                ],
            },
        },
        headers=a_headers,
    )
    assert created.status_code == 201, created.text
    video_id = created.json()["id"]
    scenes = client.get(f"/api/v1/videos/{video_id}/scenes", headers=a_headers)
    assert scenes.status_code == 200, scenes.text
    assert scenes.json()
    scene_id = scenes.json()[0]["id"]
    hidden = client.get(f"/api/v1/videos/{video_id}/scenes", headers=b_headers)
    assert hidden.status_code == 404
    patched = client.patch(
        f"/api/v1/videos/{video_id}/scenes/{scene_id}",
        headers=a_headers,
        json={"narration": "Edited narration"},
    )
    assert patched.status_code == 200
    assert patched.json()["narration"] == "Edited narration"
    status = client.get(f"/api/v1/videos/{video_id}/generation-status", headers=a_headers)
    assert status.status_code == 200


def test_stock_create_still_queues_existing_job(client):
    user = register(client, "stock-p5@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Stock", "description": ""},
        headers=headers,
    ).json()
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Stock only",
            "topic": "Stock only",
            "visual_mode": "stock",
        },
        headers=headers,
    )
    assert video.status_code == 201, video.text
    assert video.json()["latest_job"]["job_type"] == "generate_video"
    assert video.json()["latest_job"]["status"] == "QUEUED"


def test_ai_video_disabled_blocks_reservation(client, monkeypatch):
    monkeypatch.setenv("AI_VIDEO_ENABLED", "false")
    from apps.api.config import get_settings

    get_settings.cache_clear()
    user = register(client, "killswitch@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Off", "description": ""},
        headers=headers,
    ).json()
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "AI only",
            "topic": "AI only",
            "visual_mode": "ai_video",
        },
        headers=headers,
    )
    get_settings.cache_clear()
    assert video.status_code == 409
