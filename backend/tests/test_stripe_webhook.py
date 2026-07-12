from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.routers.stripe_webhook as stripe


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_mocks():
    yield

def test_webhook_invalid_signature(mocker):

    mocker.patch(
        "stripe.Webhook.construct_event",
        side_effect=stripe.stripe.error.SignatureVerificationError(
            "bad",
            "sig",
        ),
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "bad",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"


def test_webhook_parse_error(mocker):

    mocker.patch(
        "stripe.Webhook.construct_event",
        side_effect=Exception("bad payload"),
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "sig",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Webhook error"


def test_webhook_unknown_event(mocker):

    event = {
        "type": "random.event",
        "data": {
            "object": {}
        },
    }

    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=event,
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "sig",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": True}

def test_checkout_completed_dispatches_handler(mocker):

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {}
        },
    }

    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=event,
    )

    handler = mocker.patch(
        "app.routers.stripe_webhook._handle_checkout_completed"
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "sig",
        },
    )

    assert response.status_code == 200
    handler.assert_awaited_once_with({})



def test_subscription_updated_dispatches_handler(mocker):

    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {}
        },
    }

    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=event,
    )

    handler = mocker.patch(
        "app.routers.stripe_webhook._handle_subscription_updated"
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "sig",
        },
    )

    assert response.status_code == 200
    handler.assert_awaited_once_with({})



def test_subscription_deleted_dispatches_handler(mocker):

    event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {}
        },
    }

    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=event,
    )

    handler = mocker.patch(
        "app.routers.stripe_webhook._handle_subscription_deleted"
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "sig",
        },
    )

    assert response.status_code == 200
    handler.assert_awaited_once_with({})



def test_payment_failed_dispatches_handler(mocker):

    event = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {}
        },
    }

    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=event,
    )

    handler = mocker.patch(
        "app.routers.stripe_webhook._handle_payment_failed"
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "sig",
        },
    )

    assert response.status_code == 200
    handler.assert_awaited_once_with({})



def test_payment_succeeded_returns_success(mocker):

    event = {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {}
        },
    }

    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=event,
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={
            "stripe-signature": "sig",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": True}