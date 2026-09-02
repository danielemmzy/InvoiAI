from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.domain.base import TimestampedEntity


class StripeEvent(TimestampedEntity):
    """Durable Stripe webhook event used for idempotent processing."""

    stripe_event_id: str
    event_type: str
    status: str
    payload: dict[str, Any]
    attempts: int = 0
    last_error: str | None = None
    processing_started_at: datetime | None = None
    processed_at: datetime | None = None
    failed_at: datetime | None = None
