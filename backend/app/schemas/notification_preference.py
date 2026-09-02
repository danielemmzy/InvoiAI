from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationPreferenceUpdateRequest(BaseModel):
    """Update user notification preferences."""

    email_enabled: bool | None = None

    in_app_enabled: bool | None = None

    push_enabled: bool | None = None

    sms_enabled: bool | None = None


class NotificationPreferenceResponse(BaseModel):
    """Notification preferences returned to API clients."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    user_id: UUID

    email_enabled: bool

    in_app_enabled: bool

    push_enabled: bool

    sms_enabled: bool

    created_at: datetime

    updated_at: datetime