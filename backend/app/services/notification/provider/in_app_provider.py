# app/services/notification/providers/in_app_provider.py

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.domain.notification import Notification
from app.repositories.notification.notification_repository import (
    NotificationRepository,
)
from app.services.notification.provider.base import NotificationProvider


class InAppNotificationProvider(NotificationProvider):
    """
    In-app notification provider.

    Persists notifications to the notifications table.

    Responsibilities
    ----------------
    - Create in-app notification records.
    - Remain independent of HTTP/API concerns.
    - Remain independent of notification business rules.
    """

    channel = "in_app"

    def __init__(
        self,
        repository: NotificationRepository | None = None,
    ) -> None:

        self.repository = (
            repository
            or NotificationRepository()
        )

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

        notification = Notification(
            user_id=user_id,
            organization_id=organization_id,
            type=self.channel,
            title=title,
            message=message,
            data=data or {},
            channel=self.channel,
            is_read=False,
        )

        created = await self.repository.create_notification(
            notification,
        )

        return created is not None

    async def is_available(self) -> bool:
        """
        In-app delivery is available whenever
        the notification repository is configured.
        """
        return True