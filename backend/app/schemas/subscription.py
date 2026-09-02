from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import PlanType, SubscriptionStatus

"""
============================================================
Subscription Schemas

API request/response models.
============================================================
"""


# ============================================================
# Update Subscription
# ============================================================

class SubscriptionUpdate(BaseModel):

    cancel_at_period_end: bool | None = None

    metadata: dict[str, Any] | None = None


# ============================================================
# Subscription Response
# ============================================================

class SubscriptionResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    stripe_subscription_id: str

    stripe_price_id: str

    stripe_product_id: str

    plan: PlanType

    status: SubscriptionStatus

    trial_start: datetime | None

    trial_end: datetime | None

    current_period_start: datetime | None

    current_period_end: datetime | None

    cancel_at_period_end: bool

    cancelled_at: datetime | None

    document_limit: int

    metadata: dict[str, Any]

    created_at: datetime

    updated_at: datetime


# ============================================================
# Subscription List
# ============================================================

class SubscriptionListResponse(BaseModel):

    items: list[SubscriptionResponse] = Field(default_factory=list)

    total: int