from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.notification import (
    NotificationChannel,
    NotificationDeliveryStatus,
)


class NotificationDeliveryResponse(BaseModel):
    """
    Delivery lifecycle returned to API clients.

    A notification is the logical message.
    A delivery represents delivery through one
    channel/provider.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    notification_id: UUID

    user_id: UUID

    organization_id: UUID | None

    channel: NotificationChannel

    status: NotificationDeliveryStatus

    provider: str | None

    provider_message_id: str | None

    attempts: int

    last_attempt_at: datetime | None

    next_retry_at: datetime | None

    sent_at: datetime | None

    delivered_at: datetime | None

    failed_at: datetime | None

    error_code: str | None

    error_message: str | None

    metadata: dict[str, Any]

    created_at: datetime

    updated_at: datetime


class NotificationDeliveryListResponse(BaseModel):
    """Delivery records for a notification."""

    items: list[NotificationDeliveryResponse] = Field(
        default_factory=list,
    )

    total: int

    limit: int

    offset: int

    has_more: bool