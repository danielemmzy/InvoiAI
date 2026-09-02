from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.notification import NotificationChannel


class NotificationCreateRequest(BaseModel):
    """Create an in-app/application notification."""

    user_id: UUID
    organization_id: UUID | None = None

    type: str = Field(
        min_length=1,
        max_length=100,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    message: str = Field(
        min_length=1,
    )

    data: dict[str, Any] = Field(
        default_factory=dict,
    )

    channel: NotificationChannel = (
        NotificationChannel.IN_APP
    )


class NotificationUpdateRequest(BaseModel):
    """Update mutable notification fields."""

    is_read: bool | None = None


class NotificationResponse(BaseModel):
    """Notification returned to API clients."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    user_id: UUID

    organization_id: UUID | None

    type: str

    title: str

    message: str

    data: dict[str, Any]

    channel: NotificationChannel

    is_read: bool

    read_at: datetime | None

    created_at: datetime

    updated_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification collection."""

    items: list[NotificationResponse] = Field(
        default_factory=list,
    )

    total: int

    limit: int

    offset: int

    has_more: bool


class NotificationUnreadCountResponse(BaseModel):
    """Unread notification count."""

    count: int