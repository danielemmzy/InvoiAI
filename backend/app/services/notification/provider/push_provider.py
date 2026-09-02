from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.notification.provider.base import NotificationProvider


class PushNotificationProvider(NotificationProvider):
    """
    Push notification provider.

    Transport implementation is intentionally isolated from the
    notification service so Firebase, APNs, OneSignal, or another
    provider can be introduced without changing application logic.
    """

    channel = "push"

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
        Deliver a push notification.

        Push transport is not configured yet.
        """

        raise NotImplementedError(
            "Push notification provider is not configured."
        )

    async def is_available(self) -> bool:
        """
        Return whether a push provider is configured.
        """

        return False