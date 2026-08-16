from test.saas.conftest import auth_header, register


def test_invite_accept_and_isolation(client):
    owner = register(client, "owner2@example.com", name="Owner")
    owner_headers = auth_header(owner["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=owner_headers).json()[0]
    invite = client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "editor2@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["token"]

    preview = client.get(f"/api/v1/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["email"] == "editor2@example.com"

    editor = register(client, "editor2@example.com", name="Editor")
    accepted = client.post(
        "/api/v1/invites/accept",
        json={"token": token},
        headers=auth_header(editor["access_token"]),
    )
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "editor"

    members = client.get(
        f"/api/v1/workspaces/{workspace['id']}/members",
        headers=auth_header(editor["access_token"]),
    )
    assert members.status_code == 200
    assert len(members.json()) == 2

    outsider = register(client, "outsider@example.com", name="Out")
    hidden = client.get(
        f"/api/v1/workspaces/{workspace['id']}/members",
        headers=auth_header(outsider["access_token"]),
    )
    assert hidden.status_code == 404


def test_viewer_cannot_invite(client):
    owner = register(client, "lead@example.com")
    owner_headers = auth_header(owner["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=owner_headers).json()[0]
    invite = client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "view@example.com", "role": "viewer"},
        headers=owner_headers,
    ).json()
    register(client, "view@example.com", name="View")
    client.post(
        "/api/v1/invites/accept",
        json={"token": invite["token"]},
        headers=auth_header(
            client.post(
                "/api/v1/auth/login",
                json={"email": "view@example.com", "password": "password123"},
            ).json()["access_token"]
        ),
    )
    viewer_token = client.post(
        "/api/v1/auth/login",
        json={"email": "view@example.com", "password": "password123"},
    ).json()["access_token"]
    denied = client.post(
        f"/api/v1/workspaces/{workspace['id']}/invites",
        json={"email": "next@example.com", "role": "editor"},
        headers=auth_header(viewer_token),
    )
    assert denied.status_code == 403
