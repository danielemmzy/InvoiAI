from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.enum.notification import (
    NotificationChannel,
    NotificationType,
)
from app.models.domain.notification import Notification
from app.models.domain.notification_preference import (
    NotificationPreference,
)
from app.repositories.notification.notification_repository import (
    NotificationRepository,
)
from app.services.notification.notification_dispatcher import NotificationDispatcher
from app.services.notification.notification_delivery_service import NotificationDeliveryService


class NotificationService:
    """
    Application service for notifications.

    Responsibilities
    ----------------
    - Apply notification preferences.
    - Persist in-app notifications.
    - Create external notification deliveries.
    - Queue external deliveries.
    - Expose notification queries and read-state operations.

    Providers handle transport.

    Dispatcher handles delivery routing.

    Queue handles durable asynchronous processing.

    Repository handles persistence.
    """

    def __init__(
        self,
        *,
        repository: NotificationRepository | None = None,
        dispatcher: NotificationDispatcher | None = None,
        delivery_service: NotificationDeliveryService | None = None,
    ) -> None:

        self.repository = (
            repository
            or NotificationRepository()
        )

        self.dispatcher = dispatcher
        self.delivery_service = delivery_service

    # =========================================================
    # Single Channel Notification
    # =========================================================

    async def send(
        self,
        *,
        user_id: UUID,
        organization_id: UUID | None,
        type: NotificationType | str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        channel: NotificationChannel = (
            NotificationChannel.IN_APP
        ),
        recipient: str | None = None,
        template: str | None = None,
    ) -> Notification | bool | None:
        """
        Send a notification through one channel.

        In-app:
            Persist notification immediately.

        External:
            Create durable delivery and queue it.
        """

        notification_type = NotificationType(
            type,
        )

        preference = await self.get_preferences(
            user_id=user_id,
        )

        if not self._channel_enabled(
            preference,
            channel,
        ):
            return None

        payload = data or {}

        # =====================================================
        # In-App
        # =====================================================

        if channel == NotificationChannel.IN_APP:

            notification = Notification(
                user_id=user_id,
                organization_id=organization_id,
                type=notification_type.value,
                title=title,
                message=message,
                data=payload,
                channel=channel.value,
                is_read=False,
            )

            return await self.repository.create_notification(
                notification,
            )

        # =====================================================
        # External Delivery
        # =====================================================

        if self.delivery_service is None:
            raise RuntimeError(
                "NotificationDeliveryService is required for external notification delivery."
            )

        # Persist the canonical notification first so every delivery has
        # an immutable parent event for audit/read history.
        notification = Notification(
            user_id=user_id,
            organization_id=organization_id,
            type=notification_type.value,
            title=title,
            message=message,
            data=payload,
            channel=channel.value,
            is_read=False,
        )
        created_notification = await self.repository.create_notification(notification)
        if created_notification is None or created_notification.id is None:
            return False

        delivery = await self.delivery_service.create_delivery(
            notification_id=created_notification.id,
            user_id=user_id,
            organization_id=organization_id,
            channel=channel,
            recipient=recipient,
            payload={
                "title": title,
                "message": message,
                "data": payload,
                "template": template,
            },
        )
        return delivery is not None

    # =========================================================
    # Multi-Channel Delivery
    # =========================================================

    async def notify(
        self,
        *,
        user_id: UUID,
        organization_id: UUID | None,
        type: NotificationType | str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        recipient: str | None = None,
        template: str | None = None,
    ) -> dict[str, Any]:

        notification_type = NotificationType(
            type,
        )

        preference = await self.get_preferences(
            user_id=user_id,
        )

        results: dict[str, Any] = {}

        # =====================================================
        # In-App
        # =====================================================

        if preference.in_app_enabled:

            results[
                NotificationChannel.IN_APP.value
            ] = await self.send(
                user_id=user_id,
                organization_id=organization_id,
                type=notification_type,
                title=title,
                message=message,
                data=data,
                channel=NotificationChannel.IN_APP,
            )

        # =====================================================
        # Email
        # =====================================================

        if (
            preference.email_enabled
            and recipient
        ):

            results[
                NotificationChannel.EMAIL.value
            ] = await self.send(
                user_id=user_id,
                organization_id=organization_id,
                type=notification_type,
                title=title,
                message=message,
                data=data,
                channel=NotificationChannel.EMAIL,
                recipient=recipient,
                template=(
                    template
                    or notification_type.value
                ),
            )

        # =====================================================
        # Push
        # =====================================================

        if preference.push_enabled:

            results[
                NotificationChannel.PUSH.value
            ] = await self.send(
                user_id=user_id,
                organization_id=organization_id,
                type=notification_type,
                title=title,
                message=message,
                data=data,
                channel=NotificationChannel.PUSH,
            )

        # =====================================================
        # SMS
        # =====================================================

        if (
            preference.sms_enabled
            and recipient
        ):

            results[
                NotificationChannel.SMS.value
            ] = await self.send(
                user_id=user_id,
                organization_id=organization_id,
                type=notification_type,
                title=title,
                message=message,
                data=data,
                channel=NotificationChannel.SMS,
                recipient=recipient,
            )

        return results

    # =========================================================
    # Preference Handling
    # =========================================================

    @staticmethod
    def _channel_enabled(
        preference: NotificationPreference,
        channel: NotificationChannel,
    ) -> bool:

        if channel == NotificationChannel.IN_APP:
            return preference.in_app_enabled

        if channel == NotificationChannel.EMAIL:
            return preference.email_enabled

        if channel == NotificationChannel.PUSH:
            return preference.push_enabled

        if channel == NotificationChannel.SMS:
            return preference.sms_enabled

        return False

    async def get_preferences(
        self,
        *,
        user_id: UUID,
    ) -> NotificationPreference:

        preference = await self.repository.get_preferences(
            user_id=user_id,
        )

        if preference:
            return preference

        preference = NotificationPreference(
            user_id=user_id,
        )

        return await self.repository.save_preferences(
            preference,
        )

    async def update_preferences(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> NotificationPreference:

        preference = await self.get_preferences(
            user_id=user_id,
        )

        payload = preference.model_dump()

        payload.update(values)

        return await self.repository.save_preferences(
            payload,
        )

    # =========================================================
    # Read State
    # =========================================================

    async def mark_read(
        self,
        notification_id: UUID,
    ) -> Notification | None:

        return await self.repository.mark_as_read(
            notification_id,
        )

    async def mark_unread(
        self,
        notification_id: UUID,
    ) -> Notification | None:

        return await self.repository.mark_as_unread(
            notification_id,
        )

    async def mark_all_read(
        self,
        *,
        user_id: UUID,
    ) -> bool:

        return await self.repository.mark_all_as_read(
            user_id=user_id,
        )

    # =========================================================
    # Queries
    # =========================================================

    async def get(
        self,
        notification_id: UUID,
    ) -> Notification | None:

        return await self.repository.get_notification(
            notification_id,
        )

    async def list_notifications(
        self,
        *,
        user_id: UUID,
        limit: int = 25,
        offset: int = 0,
    ) -> list[Notification]:

        return await self.repository.list_user_notifications(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    async def unread(
        self,
        *,
        user_id: UUID,
    ) -> list[Notification]:

        return await self.repository.unread_notifications(
            user_id=user_id,
        )

    async def unread_count(
        self,
        *,
        user_id: UUID,
    ) -> int:

        return await self.repository.unread_count(
            user_id=user_id,
        )