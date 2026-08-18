from apps.api.services.integrations_service import SocialSettings, StripeSettings
from test.saas.conftest import auth_header, register


def test_social_and_stripe_settings_require_auth(client):
    assert client.get("/api/v1/settings/social").status_code == 401
    assert client.get("/api/v1/settings/stripe").status_code == 401


def test_social_and_stripe_settings_save(client, monkeypatch):
    social_store = {
        "configured": False,
        "enabled": False,
        "username_set": False,
        "platforms": ["tiktok", "instagram", "youtube"],
        "message": "not configured",
    }
    stripe_store = {
        "provider": "local",
        "live_ready": False,
        "secret_set": False,
        "webhook_set": False,
        "webhook_url": "http://127.0.0.1:8000/api/v1/billing/webhooks/stripe",
        "public_api_url": "http://127.0.0.1:8000",
        "message": "local",
    }

    def social_status():
        return SocialSettings(**social_store)

    def update_social(payload):
        if payload.api_key.strip() and payload.username.strip() and payload.enabled:
            social_store["configured"] = True
            social_store["enabled"] = True
            social_store["username_set"] = True
            social_store["message"] = "ready"
        if payload.platforms:
            social_store["platforms"] = payload.platforms
        return social_status()

    def stripe_status():
        return StripeSettings(**stripe_store)

    def update_stripe(payload):
        if payload.secret_key.strip():
            stripe_store["secret_set"] = True
        if payload.webhook_secret.strip():
            stripe_store["webhook_set"] = True
        if payload.enable and stripe_store["secret_set"] and stripe_store["webhook_set"]:
            stripe_store["provider"] = "stripe"
            stripe_store["live_ready"] = True
            stripe_store["message"] = "live"
        return stripe_status()

    monkeypatch.setattr("apps.api.api.routes.settings.integrations_service.social_status", social_status)
    monkeypatch.setattr("apps.api.api.routes.settings.integrations_service.update_social", update_social)
    monkeypatch.setattr("apps.api.api.routes.settings.integrations_service.stripe_status", stripe_status)
    monkeypatch.setattr("apps.api.api.routes.settings.integrations_service.update_stripe", update_stripe)

    user = register(client, "integrations@example.com")
    headers = auth_header(user["access_token"])

    social = client.put(
        "/api/v1/settings/social",
        headers=headers,
        json={
            "api_key": "up_test_key",
            "username": "shortgen",
            "enabled": True,
            "platforms": ["tiktok", "instagram", "youtube"],
        },
    )
    assert social.status_code == 200, social.text
    body = social.json()
    assert body["configured"] is True
    assert "up_test_key" not in social.text

    stripe = client.put(
        "/api/v1/settings/stripe",
        headers=headers,
        json={"secret_key": "sk_test_x", "webhook_secret": "whsec_x", "enable": True},
    )
    assert stripe.status_code == 200, stripe.text
    billed = stripe.json()
    assert billed["live_ready"] is True
    assert billed["provider"] == "stripe"
    assert "sk_test_x" not in stripe.text
    assert "whsec_x" not in stripe.text
