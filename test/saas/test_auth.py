from test.saas.conftest import auth_header, register


def test_register_creates_user_and_workspace(client):
    payload = register(client, "ada@example.com", name="Ada Lovelace")
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "ada@example.com"
    me = client.get("/api/v1/auth/me", headers=auth_header(payload["access_token"]))
    assert me.status_code == 200
    assert me.json()["name"] == "Ada Lovelace"
    workspaces = client.get("/api/v1/workspaces", headers=auth_header(payload["access_token"]))
    assert workspaces.status_code == 200
    assert len(workspaces.json()) == 1
    assert workspaces.json()[0]["role"] == "owner"


def test_login_returns_jwt(client):
    register(client, "login@example.com", password="supersecret")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "supersecret"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_rejects_bad_password(client):
    register(client, "badpass@example.com", password="supersecret")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "badpass@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_jwt(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_duplicate_register_is_conflict(client):
    register(client, "dup@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123", "name": "Dup"},
    )
    assert response.status_code == 409
