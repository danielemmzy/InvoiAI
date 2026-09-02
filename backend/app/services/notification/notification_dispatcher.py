from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.enum.notification import NotificationChannel
from app.services.notification.provider.base import NotificationProvider
from app.services.notification.provider.email_provider import (
    EmailNotificationProvider,
)
from app.services.notification.provider.in_app_provider import (
    InAppNotificationProvider,
)
from app.services.notification.provider.push_provider import (
    PushNotificationProvider,
)
from app.services.notification.provider.sms_provider import (
    SMSNotificationProvider,
)
from app.services.notification.queue.base import NotificationQueue


class NotificationDispatcher:
    """
    Notification delivery dispatcher.

    Responsibilities
    ----------------
    - Resolve notification providers.
    - Queue notification deliveries.
    - Process claimed deliveries through providers.
    - Keep transport-specific logic outside business services.

    The dispatcher does NOT contain notification business rules.

    Architecture
    ------------

        NotificationService
                |
                v
        NotificationDispatcher
                |
                v
        NotificationQueue
                |
                v
        notification_deliveries
                |
                v
        NotificationWorker
                |
                v
        NotificationDispatcher.process()
                |
                +---- InAppProvider
                +---- EmailProvider
                +---- PushProvider
                +---- SMSProvider
    """

    def __init__(
        self,
        *,
        queue: NotificationQueue,
        providers: dict[
            NotificationChannel,
            NotificationProvider,
        ]
        | None = None,
    ) -> None:

        self.queue = queue

        self.providers = providers or {
            NotificationChannel.IN_APP:
                InAppNotificationProvider(),

            NotificationChannel.EMAIL:
                EmailNotificationProvider(),

            NotificationChannel.PUSH:
                PushNotificationProvider(),

            NotificationChannel.SMS:
                SMSNotificationProvider(),
        }

    # =========================================================
    # Provider Registration
    # =========================================================

    def register(
        self,
        provider: NotificationProvider,
    ) -> None:
        """
        Register or replace a notification provider.
        """

        channel = NotificationChannel(
            provider.channel,
        )

        self.providers[channel] = provider

    # =========================================================
    # Provider Resolution
    # =========================================================

    def get_provider(
        self,
        channel: NotificationChannel,
    ) -> NotificationProvider | None:

        return self.providers.get(channel)

    # =========================================================
    # Queue Delivery
    # =========================================================

    async def dispatch(
        self,
        *,
        delivery_id: UUID,
        user_id: UUID,
        title: str,
        message: str,
        channel: NotificationChannel,
        organization_id: UUID | None = None,
        recipient: str | None = None,
        template: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Queue a notification delivery.

        This method does NOT directly send the notification.

        A worker will later claim the delivery and call
        process().
        """

        provider = self.get_provider(
            channel,
        )

        if provider is None:
            return False

        payload: dict[str, Any] = {
            "delivery_id": str(delivery_id),
            "user_id": str(user_id),
            "organization_id": (
                str(organization_id)
                if organization_id
                else None
            ),
            "title": title,
            "message": message,
            "channel": channel.value,
            "recipient": recipient,
            "template": template,
            "data": data or {},
        }

        return await self.queue.enqueue(
            delivery_id=delivery_id,
            payload=payload,
        )

    # =========================================================
    # Process Delivery
    # =========================================================

    async def process(
        self,
        *,
        delivery: dict[str, Any],
    ) -> bool:
        """Deliver one already-claimed delivery through its provider.

        Queue state transitions are intentionally owned by NotificationWorker.
        """
        channel = NotificationChannel(delivery["channel"])
        provider = self.get_provider(channel)
        if provider is None or not await provider.is_available():
            return False

        payload = delivery.get("payload") or {}
        return await provider.send(
            user_id=UUID(str(delivery["user_id"])),
            title=payload.get("title", delivery.get("title", "")),
            message=payload.get("message", delivery.get("message", "")),
            data=payload.get("data") or delivery.get("data") or {},
            organization_id=(
                UUID(str(delivery["organization_id"]))
                if delivery.get("organization_id")
                else None
            ),
            recipient=delivery.get("recipient"),
            template=payload.get("template") or delivery.get("template"),
        )

    # =========================================================
    # Process Batch
    # =========================================================

    async def process_batch(
        self,
        *,
        limit: int = 10,
    ) -> dict[str, int]:
        """Compatibility helper; lifecycle is owned by NotificationWorker."""
        deliveries = await self.queue.claim(limit=limit)
        successful = 0
        failed = 0
        for delivery in deliveries:
            if await self.process(delivery=delivery):
                successful += 1
            else:
                failed += 1
        return {"claimed": len(deliveries), "successful": successful, "failed": failed}
