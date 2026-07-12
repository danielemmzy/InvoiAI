from types import SimpleNamespace

import stripe
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import AuthUser, get_current_user
from app.routers import billing


client = TestClient(app)


def override_user():
    return AuthUser(
        id="user-1",
        email="user@test.com",
        plan="starter",
    )


app.dependency_overrides[get_current_user] = override_user


@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides[get_current_user] = override_user


def test_get_price_id_known():
    assert billing.get_price_id("starter")
    assert billing.get_price_id("pro")


def test_get_price_id_unknown():
    assert billing.get_price_id("gold") == ""

def test_checkout_invalid_plan():

    response = client.post(
        "/billing/checkout",
        json={
            "plan": "gold",
            "success_url": "https://success.com",
            "cancel_url": "https://cancel.com",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid plan. Choose 'starter' or 'pro'."
    )


def test_checkout_plan_not_configured(mocker):

    mocker.patch(
        "app.routers.billing.get_price_id",
        return_value="",
    )

    response = client.post(
        "/billing/checkout",
        json={
            "plan": "starter",
            "success_url": "https://success.com",
            "cancel_url": "https://cancel.com",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Plan not configured. Contact support."
    )


def test_checkout_success(mocker):

    profile = SimpleNamespace(
        data={
            "stripe_customer_id": None
        }
    )

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = profile

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.billing.get_supabase",
        return_value=supabase,
    )

    mocker.patch(
        "app.routers.billing.get_price_id",
        return_value="price_123",
    )

    session = SimpleNamespace(
        id="sess_123",
        url="https://checkout.stripe.com/test",
    )

    create = mocker.patch(
        "stripe.checkout.Session.create",
        return_value=session,
    )

    response = client.post(
        "/billing/checkout",
        json={
            "plan": "starter",
            "success_url": "https://success.com",
            "cancel_url": "https://cancel.com",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["checkout_url"] == session.url
    assert body["session_id"] == session.id

    create.assert_called_once()


def test_get_subscription_success(mocker):

    subscription = SimpleNamespace(
        data={
            "status": "active",
            "stripe_subscription_id": "sub_123",
        }
    )

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = subscription

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.billing.get_supabase",
        return_value=supabase,
    )

    mocker.patch(
        "app.routers.billing.get_usage_summary",
        return_value={
            "used": 1,
            "limit": 5,
            "remaining": 4,
            "plan": "starter",
            "month": "2026-07",
            "limit_reached": False,
        },
    )

    response = client.get("/billing/subscription")

    assert response.status_code == 200

    body = response.json()

    assert body["plan"] == "starter"
    assert body["subscription"]["status"] == "active"
    assert body["usage"]["used"] == 1


def test_get_subscription_no_subscription(mocker):

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.side_effect = Exception("db")

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.billing.get_supabase",
        return_value=supabase,
    )

    mocker.patch(
        "app.routers.billing.get_usage_summary",
        return_value={
            "used": 0,
            "limit": 5,
            "remaining": 5,
            "plan": "starter",
            "month": "2026-07",
            "limit_reached": False,
        },
    )

    response = client.get("/billing/subscription")

    assert response.status_code == 200

    body = response.json()

    assert body["subscription"] is None
    assert body["usage"]["remaining"] == 5

def test_cancel_subscription_success(mocker):

    subscription = SimpleNamespace(
        data={
            "stripe_subscription_id": "sub_123",
        }
    )

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.update.return_value = table
    table.execute.return_value = subscription

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.billing.get_supabase",
        return_value=supabase,
    )

    modify = mocker.patch(
        "stripe.Subscription.modify"
    )

    response = client.post("/billing/cancel")

    assert response.status_code == 200

    body = response.json()

    assert "cancel" in body["message"].lower()

    modify.assert_called_once_with(
        "sub_123",
        cancel_at_period_end=True,
    )


def test_cancel_subscription_not_found(mocker):

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.side_effect = Exception("db")

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.billing.get_supabase",
        return_value=supabase,
    )

    response = client.post("/billing/cancel")

    assert response.status_code == 404

    assert response.json()["detail"] == "No active subscription found"