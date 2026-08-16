from test.saas.conftest import auth_header, register


def _seed(client, email: str):
    user = register(client, email)
    headers = auth_header(user["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Channel", "description": ""},
        headers=headers,
    ).json()
    return user, headers, workspace, project


def test_create_video_creates_queued_job(client):
    _, headers, workspace, project = _seed(client, "video@example.com")
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Ocean facts",
            "topic": "Amazing ocean facts",
            "video_language": "en-US",
            "duration": 30,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "voice": "en-US-JennyNeural-Female",
            "visual_source": "stock",
        },
        headers=headers,
    )
    assert video.status_code == 201, video.text
    body = video.json()
    assert body["status"] == "queued"
    assert body["latest_job"]["status"] == "QUEUED"
    job = client.get(f"/api/v1/jobs/{body['latest_job']['id']}", headers=headers)
    assert job.status_code == 200
    assert job.json()["current_stage"] == "QUEUED"


def test_cancel_job(client):
    _, headers, workspace, project = _seed(client, "cancel@example.com")
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Cancel me",
            "topic": "Cancel me",
        },
        headers=headers,
    ).json()
    job_id = video["latest_job"]["id"]
    cancelled = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


def test_user_cannot_read_foreign_video_or_job(client):
    _, alice_headers, workspace, project = _seed(client, "owner@example.com")
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Private",
            "topic": "Private topic",
        },
        headers=alice_headers,
    ).json()
    bob = register(client, "intruder@example.com", name="Bob")
    bob_headers = auth_header(bob["access_token"])
    assert client.get(f"/api/v1/videos/{video['id']}", headers=bob_headers).status_code == 404
    assert client.get(f"/api/v1/jobs/{video['latest_job']['id']}", headers=bob_headers).status_code == 404
