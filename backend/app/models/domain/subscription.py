"""
============================================================
Subscription Domain Model

Mirrors PostgreSQL table.

- subscriptions
============================================================
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import PlanType, SubscriptionStatus
from app.models.domain.base import TimestampedEntity


JsonDict = dict[str, Any]


class Subscription(TimestampedEntity):
    """
    Mirrors subscriptions table.
    """

    org_id: UUID

    stripe_subscription_id: str | None = None

    stripe_price_id: str | None = None

    stripe_product_id: str | None = None

    plan: PlanType

    status: SubscriptionStatus

    trial_start: datetime | None = None

    trial_end: datetime | None = None

    current_period_start: datetime | None = None

    current_period_end: datetime | None = None

    cancel_at_period_end: bool

    cancelled_at: datetime | None = None

    document_limit: int

    metadata: JsonDict = Field(default_factory=dict)