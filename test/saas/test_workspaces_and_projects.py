from test.saas.conftest import auth_header, register


def test_create_workspace_and_project(client):
    user = register(client, "ws@example.com")
    headers = auth_header(user["access_token"])
    workspace = client.post("/api/v1/workspaces", json={"name": "Studio"}, headers=headers)
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace_id, "name": "Launch", "description": "First batch"},
        headers=headers,
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    fetched = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Launch"

    listed = client.get("/api/v1/projects", headers=headers)
    assert any(item["id"] == project_id for item in listed.json())


def test_user_cannot_access_foreign_workspace(client):
    alice = register(client, "alice@example.com", name="Alice")
    bob = register(client, "bob@example.com", name="Bob")
    alice_ws = client.get("/api/v1/workspaces", headers=auth_header(alice["access_token"])).json()[0]
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": alice_ws["id"], "name": "Secret", "description": ""},
        headers=auth_header(alice["access_token"]),
    )
    assert project.status_code == 201

    bob_headers = auth_header(bob["access_token"])
    listed = client.get(
        "/api/v1/projects",
        params={"workspace_id": alice_ws["id"]},
        headers=bob_headers,
    )
    assert listed.status_code == 404

    foreign = client.get(f"/api/v1/projects/{project.json()['id']}", headers=bob_headers)
    assert foreign.status_code == 404
