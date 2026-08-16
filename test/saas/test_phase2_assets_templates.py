from test.saas.conftest import auth_header, register


def test_asset_upload_and_isolation(client):
    alice = register(client, "alice-lib@example.com")
    alice_headers = auth_header(alice["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=alice_headers).json()[0]
    uploaded = client.post(
        "/api/v1/assets",
        data={"workspace_id": workspace["id"]},
        files={"file": ("clip.mp4", b"fake-mp4-bytes", "video/mp4")},
        headers=alice_headers,
    )
    assert uploaded.status_code == 201, uploaded.text
    asset_id = uploaded.json()["id"]
    listed = client.get("/api/v1/assets", params={"workspace_id": workspace["id"]}, headers=alice_headers)
    assert any(item["id"] == asset_id for item in listed.json())

    bob = register(client, "bob-lib@example.com")
    hidden = client.get(
        "/api/v1/assets",
        params={"workspace_id": workspace["id"]},
        headers=auth_header(bob["access_token"]),
    )
    assert hidden.status_code == 404


def test_reject_disallowed_upload(client):
    user = register(client, "upload@example.com")
    headers = auth_header(user["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    rejected = client.post(
        "/api/v1/assets",
        data={"workspace_id": workspace["id"]},
        files={"file": ("payload.exe", b"mz", "application/octet-stream")},
        headers=headers,
    )
    assert rejected.status_code == 400


def test_system_templates_and_workspace_template(client):
    user = register(client, "tmpl@example.com")
    headers = auth_header(user["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    listed = client.get("/api/v1/templates", params={"workspace_id": workspace["id"]}, headers=headers)
    assert listed.status_code == 200
    assert any(item["is_system"] for item in listed.json())
    created = client.post(
        "/api/v1/templates",
        json={
            "workspace_id": workspace["id"],
            "name": "Brand short",
            "description": "Internal",
            "config": {"aspect_ratio": "9:16", "duration": 20},
        },
        headers=headers,
    )
    assert created.status_code == 201
    again = client.get("/api/v1/templates", params={"workspace_id": workspace["id"]}, headers=headers)
    assert any(item["name"] == "Brand short" for item in again.json())


def test_local_video_requires_assets(client):
    user = register(client, "localvid@example.com")
    headers = auth_header(user["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Local", "description": ""},
        headers=headers,
    ).json()
    missing = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Local only",
            "topic": "Local only",
            "visual_source": "local",
        },
        headers=headers,
    )
    assert missing.status_code == 400

    asset = client.post(
        "/api/v1/assets",
        data={"workspace_id": workspace["id"]},
        files={"file": ("bg.mp4", b"bytes", "video/mp4")},
        headers=headers,
    ).json()
    created = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Local ready",
            "topic": "Local ready",
            "visual_source": "local",
            "asset_ids": [asset["id"]],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["latest_job"]["input_data"]["asset_ids"] == [asset["id"]]
