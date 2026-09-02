from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.notification.provider.base import NotificationProvider


class SMSNotificationProvider(NotificationProvider):
    """
    SMS notification provider.

    The transport is deliberately isolated so a provider such as
    Twilio, AWS SNS, or another SMS gateway can be added later.
    """

    channel = "sms"

    async def send(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        organization_id: UUID | None = None,
        recipient: str | None = None,
        template: str | None = None,
    ) -> bool:
        """
        Deliver an SMS notification.

        SMS transport is not configured yet.
        """

        raise NotImplementedError(
            "SMS notification provider is not configured."
        )

    async def is_available(self) -> bool:
        """
        Return whether an SMS provider is configured.
        """

        return False