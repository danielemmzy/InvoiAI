"""
============================================================
Profile Domain Models

Mirror PostgreSQL tables.

- profiles
- subscriptions
============================================================
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import PlanType, SubscriptionStatus
from app.models.domain.base import DomainModel

JsonDict = dict[str, Any]


# ============================================================
# Profile
# ============================================================

class Profile(DomainModel):
    """
    Mirrors profiles table.
    """

    id: UUID

    full_name: str | None = None

    avatar_url: str | None = None

    job_title: str | None = None

    department: str | None = None

    phone: str | None = None

    timezone: str | None = None

    language: str | None = None

    notification_prefs: JsonDict = Field(default_factory=dict)

    ui_preferences: JsonDict = Field(default_factory=dict)

    onboarding_completed: bool

    onboarding_step: int

    last_active_at: datetime | None = None

    created_at: datetime

    updated_at: datetime


# ============================================================
# Subscription
# ============================================================

class Subscription(DomainModel):
    """
    Mirrors subscriptions table.
    """

    id: UUID

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

    created_at: datetime

    updated_at: datetime