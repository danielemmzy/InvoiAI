from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationPreference(BaseModel):
    """
    User notification delivery preferences.
    """

    id: UUID | None = None

    user_id: UUID

    email_enabled: bool = True

    in_app_enabled: bool = True

    push_enabled: bool = False

    sms_enabled: bool = False

    created_at: datetime | None = None

    updated_at: datetime | None = None