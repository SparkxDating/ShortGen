"""Monthly subscription credits are granted from invoices, once per invoice."""

from shared.billing.interface import WebhookResult
from test.saas.conftest import auth_header, register


def _workspace(client, headers):
    return client.get("/api/v1/workspaces", headers=headers).json()[0]


def _usage(client, headers, workspace_id):
    response = client.get("/api/v1/billing/usage", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_plans_are_public(client):
    response = client.get("/api/v1/billing/plans")
    assert response.status_code == 200, response.text
    slugs = {plan["slug"]: plan for plan in response.json()}
    assert slugs["starter"]["price_cents"] == 1900
    assert slugs["starter"]["monthly_credits"] == 500
    assert slugs["pro"]["price_cents"] == 4900


def test_invoice_paid_grants_once_then_renews(client):
    user = register(client, "subscriber@example.com")
    headers = auth_header(user["access_token"])
    workspace = _workspace(client, headers)
    starter = next(plan for plan in client.get("/api/v1/billing/plans").json() if plan["slug"] == "starter")
    before = _usage(client, headers, workspace["id"])["available"]

    from apps.api.database.session import SessionLocal
    from apps.api.services.billing_service import apply_provider_event

    def invoice(event_id: str, reason: str) -> WebhookResult:
        return WebhookResult(
            event_id=event_id,
            event_type="invoice.paid",
            workspace_id=workspace["id"],
            kind="plan",
            item_id=starter["id"],
            payload={"billing_reason": reason, "customer": "cus_test", "subscription": "sub_test"},
            customer_id="cus_test",
            subscription_id="sub_test",
            mode="subscription",
        )

    db = SessionLocal()
    apply_provider_event(db, "stripe", invoice("in_001", "subscription_create"))
    apply_provider_event(db, "stripe", invoice("in_001", "subscription_create"))
    db.close()
    assert _usage(client, headers, workspace["id"])["available"] == before + starter["monthly_credits"]

    db = SessionLocal()
    apply_provider_event(db, "stripe", invoice("in_002", "subscription_cycle"))
    db.close()
    renewed = _usage(client, headers, workspace["id"])
    assert renewed["available"] == before + (starter["monthly_credits"] * 2)
    assert renewed["plan"]["slug"] == "starter"
    assert renewed["subscription_status"] == "active"

    db = SessionLocal()
    apply_provider_event(
        db,
        "stripe",
        WebhookResult(
            event_id="evt_cancel",
            event_type="customer.subscription.deleted",
            workspace_id=workspace["id"],
            kind="plan",
            item_id=starter["id"],
            payload={"status": "canceled", "id": "sub_test"},
            customer_id="cus_test",
            subscription_id="sub_test",
        ),
    )
    db.close()
    canceled = _usage(client, headers, workspace["id"])
    assert canceled["subscription_status"] == "canceled"
    assert canceled["available"] == before + (starter["monthly_credits"] * 2)
