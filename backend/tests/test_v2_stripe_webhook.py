from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app2.services.billing.stripe_event_processor import StripeEventProcessor


class FakeEvents:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = None
        self.processed = []
        self.failed = []
        self.processing = []

    async def get_by_stripe_event_id(self, event_id):
        return self.existing

    async def create_event(self, **kwargs):
        self.created = kwargs
        self.existing = SimpleNamespace(id=uuid4(), status="processing")
        return self.existing

    async def mark_processing(self, event_id):
        self.processing.append(event_id)
        self.existing.status = "processing"
        return True

    async def mark_processed(self, event_id):
        self.processed.append(event_id)
        return True

    async def mark_failed(self, event_id, error):
        self.failed.append((event_id, error))
        return True


class FakeOrganizations:
    def __init__(self):
        self.updates = []

    async def get_by_stripe_customer(self, customer_id):
        return None

    async def update_plan(self, org_id, plan):
        self.updates.append((org_id, plan))

    async def update_organization(self, org_id, data):
        self.updates.append((org_id, data))


class FakeSubscriptions:
    def __init__(self):
        self.by_org = None
        self.by_stripe = None
        self.updated = []
        self.created = []

    async def get_by_org(self, org_id):
        return self.by_org

    async def get_by_stripe_subscription(self, subscription_id):
        return self.by_stripe

    async def update_subscription(self, subscription_id, data):
        self.updated.append((subscription_id, data))

    async def create_subscription(self, data):
        self.created.append(data)

    async def mark_cancelled(self, subscription_id):
        self.updated.append((subscription_id, {"status": "canceled"}))

    async def update_status(self, subscription_id, status):
        self.updated.append((subscription_id, status))


@pytest.mark.asyncio
async def test_stripe_event_is_idempotent():
    event_id = uuid4()
    existing = SimpleNamespace(id=event_id, status="processed")
    events = FakeEvents(existing=existing)
    processor = StripeEventProcessor(
        events=events,
        organizations=FakeOrganizations(),
        subscriptions=FakeSubscriptions(),
    )

    processed = await processor.process({
        "event_id": "evt_123",
        "event_type": "checkout.session.completed",
        "object": {},
    })

    assert processed is False
    assert not events.processed
    assert not events.created


@pytest.mark.asyncio
async def test_checkout_completed_upgrades_organization(monkeypatch):
    org_id = uuid4()
    events = FakeEvents()
    organizations = FakeOrganizations()
    subscriptions = FakeSubscriptions()
    processor = StripeEventProcessor(
        events=events,
        organizations=organizations,
        subscriptions=subscriptions,
    )

    class FakeStripeSubscription:
        @staticmethod
        def retrieve(_subscription_id):
            return {
                "id": "sub_123",
                "status": "active",
                "metadata": {"org_id": str(org_id)},
                "items": {"data": [{"price": {"id": "price_pro", "product": "prod_pro"}}]},
                "cancel_at_period_end": False,
            }

    monkeypatch.setattr("stripe.Subscription.retrieve", FakeStripeSubscription.retrieve)
    monkeypatch.setattr("app.services.billing.stripe_event_processor.settings.stripe_price_pro", "price_pro")
    monkeypatch.setattr("app.services.billing.stripe_event_processor.settings.stripe_price_starter", "price_starter")

    result = await processor.process({
        "event_id": "evt_checkout",
        "event_type": "checkout.session.completed",
        "object": {
            "id": "cs_123",
            "customer": "cus_123",
            "subscription": "sub_123",
            "metadata": {"org_id": str(org_id)},
        },
    })

    assert result is True
    assert events.processed
    assert subscriptions.created
    assert organizations.updates


@pytest.mark.asyncio
async def test_failed_stripe_event_is_recorded():
    events = FakeEvents()
    processor = StripeEventProcessor(
        events=events,
        organizations=FakeOrganizations(),
        subscriptions=FakeSubscriptions(),
    )

    with pytest.raises(ValueError):
        await processor.process({
            "event_id": "evt_bad",
            "event_type": "checkout.session.completed",
            "object": {"subscription": "sub_missing_org"},
        })

    assert events.failed

@pytest.mark.asyncio
async def test_subscription_deleted_downgrades_to_free():
    org_id = uuid4()
    events = FakeEvents()
    organizations = FakeOrganizations()
    subscriptions = FakeSubscriptions()
    subscriptions.by_stripe = SimpleNamespace(id=uuid4(), org_id=org_id)
    processor = StripeEventProcessor(
        events=events,
        organizations=organizations,
        subscriptions=subscriptions,
    )

    result = await processor.process({
        "event_id": "evt_deleted",
        "event_type": "customer.subscription.deleted",
        "object": {"id": "sub_123"},
    })

    assert result is True
    assert any(update[0] == org_id for update in organizations.updates if isinstance(update, tuple))


@pytest.mark.asyncio
async def test_payment_failed_marks_subscription_past_due():
    events = FakeEvents()
    organizations = FakeOrganizations()
    subscriptions = FakeSubscriptions()
    subscriptions.by_stripe = SimpleNamespace(id=uuid4(), org_id=uuid4())
    processor = StripeEventProcessor(
        events=events,
        organizations=organizations,
        subscriptions=subscriptions,
    )

    result = await processor.process({
        "event_id": "evt_failed",
        "event_type": "invoice.payment_failed",
        "object": {"subscription": "sub_123"},
    })

    assert result is True
    assert subscriptions.updated
