from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enum.notification import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationProvider,
)


class NotificationDelivery(BaseModel):
    """Durable delivery state for one notification/channel pair."""

    id: UUID | None = None
    notification_id: UUID
    user_id: UUID
    organization_id: UUID | None = None
    channel: NotificationChannel
    provider: NotificationProvider
    status: NotificationDeliveryStatus = NotificationDeliveryStatus.QUEUED
    idempotency_key: str | None = None
    recipient: str | None = None
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    failed_at: datetime | None = None
    provider_message_id: str | None = None
    provider_error_code: str | None = None
    provider_response: dict[str, Any] = Field(default_factory=dict)
    next_retry_at: datetime | None = None
    queued_at: datetime | None = None
    processing_started_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
