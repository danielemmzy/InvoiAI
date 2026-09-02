from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Notification(BaseModel):
    """
    Domain model for user notifications.
    """

    id: UUID | None = None

    user_id: UUID

    organization_id: UUID | None = None

    type: str

    title: str

    message: str

    data: dict = Field(
        default_factory=dict,
    )

    channel: str = "in_app"

    is_read: bool = False

    read_at: datetime | None = None

    created_at: datetime | None = None

    updated_at: datetime | None = None