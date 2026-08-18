from apps.api.services.provider_keys_service import ProviderKeyStatus, ProviderKeysResponse
from test.saas.conftest import auth_header, register


def test_provider_keys_require_auth(client):
    assert client.get("/api/v1/settings/keys").status_code == 401


def test_provider_keys_save_and_report_configured(client, monkeypatch):
    store = {
        "llm_provider": "moonshot",
        "gemini": False,
        "pexels": False,
    }

    def status():
        return ProviderKeysResponse(
            llm_provider=store["llm_provider"],
            keys=[
                ProviderKeyStatus(id="kimi", label="Kimi / Moonshot", configured=False, llm_provider="moonshot"),
                ProviderKeyStatus(id="openai", label="OpenAI", configured=False, llm_provider="openai"),
                ProviderKeyStatus(
                    id="gemini",
                    label="Google Gemini",
                    configured=store["gemini"],
                    llm_provider="gemini",
                ),
                ProviderKeyStatus(id="deepseek", label="DeepSeek", configured=False, llm_provider="deepseek"),
                ProviderKeyStatus(id="pexels", label="Pexels", configured=store["pexels"]),
            ],
        )

    def update(payload):
        if payload.llm_provider:
            store["llm_provider"] = payload.llm_provider
        if payload.gemini.strip():
            store["gemini"] = True
        if payload.pexels.strip():
            store["pexels"] = True
        return status()

    monkeypatch.setattr("apps.api.api.routes.settings.provider_keys_service.status", status)
    monkeypatch.setattr("apps.api.api.routes.settings.provider_keys_service.update", update)

    user = register(client, "keys@example.com")
    headers = auth_header(user["access_token"])
    listed = client.get("/api/v1/settings/keys", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["llm_provider"] == "moonshot"

    saved = client.put(
        "/api/v1/settings/keys",
        headers=headers,
        json={"llm_provider": "gemini", "gemini": "test-gemini-key", "pexels": "pexels-test"},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["llm_provider"] == "gemini"
    by_id = {item["id"]: item for item in body["keys"]}
    assert by_id["gemini"]["configured"] is True
    assert by_id["pexels"]["configured"] is True
    assert "test-gemini-key" not in saved.text
