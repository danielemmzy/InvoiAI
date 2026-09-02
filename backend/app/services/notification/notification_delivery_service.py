from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.enum.notification import NotificationChannel, NotificationDeliveryStatus, NotificationProvider
from app.models.domain.notification_delivery import NotificationDelivery
from app.repositories.notification.notification_delivery_repository import NotificationDeliveryRepository
from app.services.notification.queue.base import NotificationQueue
from app.services.notification.queue.database_queue import DatabaseNotificationQueue


class NotificationDeliveryService:
    """Application service for durable notification delivery state."""

    MAX_ATTEMPTS = 5
    RETRY_DELAYS = (60, 300, 900, 3600, 21600)

    def __init__(
        self,
        *,
        db=None,
        queue: NotificationQueue | None = None,
        repository: NotificationDeliveryRepository | None = None,
    ) -> None:
        self.repository = repository or NotificationDeliveryRepository()
        self.queue = queue or (DatabaseNotificationQueue(db) if db is not None else None)
        if self.queue is None:
            raise ValueError("Either queue or db must be provided.")

    async def create_delivery(
        self,
        *,
        notification_id: UUID,
        user_id: UUID,
        organization_id: UUID | None,
        channel: NotificationChannel,
        provider: str | NotificationProvider | None = None,
        recipient: str | None = None,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        enqueue: bool = True,
    ) -> NotificationDelivery | None:
        existing = await self.repository.get_channel_delivery(
            notification_id=notification_id,
            channel=channel,
        )
        if existing:
            return existing

        default_provider = {
            NotificationChannel.IN_APP: NotificationProvider.IN_APP,
            NotificationChannel.EMAIL: NotificationProvider.SMTP,
            NotificationChannel.PUSH: NotificationProvider.FCM,
            NotificationChannel.SMS: NotificationProvider.TWILIO,
        }[channel]
        selected_provider = NotificationProvider(provider) if provider else default_provider

        delivery = NotificationDelivery(
            notification_id=notification_id,
            user_id=user_id,
            organization_id=organization_id,
            channel=channel,
            provider=selected_provider,
            status=NotificationDeliveryStatus.QUEUED,
            recipient=recipient,
            payload=payload or {},
            metadata=metadata or {},
        )
        created = await self.repository.create_delivery(delivery)
        if created is None:
            return None

        if enqueue and created.id:
            queue_payload = dict(created.payload or {})
            queue_payload.setdefault("delivery_id", str(created.id))
            queue_payload.setdefault("channel", channel.value)
            queue_payload.setdefault("recipient", recipient)
            queue_payload.setdefault("provider", str(selected_provider))
            await self.enqueue(
                delivery_id=created.id,
                payload=queue_payload,
            )
        return created

    async def get(self, delivery_id: UUID) -> NotificationDelivery | None:
        return await self.repository.get_delivery(delivery_id)

    async def enqueue(self, *, delivery_id: UUID, payload: dict[str, Any] | None = None) -> bool:
        delivery = await self.get(delivery_id)
        if delivery is None:
            return False
        if delivery.status in {NotificationDeliveryStatus.SENT, NotificationDeliveryStatus.DELIVERED, NotificationDeliveryStatus.CANCELLED}:
            return False
        return await self.queue.enqueue(delivery_id=delivery_id, payload=payload or {})

    async def queued(self, *, limit: int = 100) -> list[NotificationDelivery]:
        return await self.repository.list_queued(limit=limit)

    async def start_processing(self, delivery_id: UUID) -> NotificationDelivery | None:
        delivery = await self.get(delivery_id)
        if delivery is None:
            return None
        if delivery.status not in {NotificationDeliveryStatus.QUEUED, NotificationDeliveryStatus.RETRYING}:
            return delivery
        if delivery.attempt_count >= self.MAX_ATTEMPTS:
            return await self.fail(
                delivery_id,
                error_code="MAX_ATTEMPTS_EXCEEDED",
                error_message="Maximum delivery attempts exceeded.",
            )
        await self.repository.increment_attempt(delivery_id)
        return await self.repository.mark_processing(delivery_id)

    async def increment_attempt(self, delivery_id: UUID) -> NotificationDelivery | None:
        return await self.repository.increment_attempt(delivery_id)

    async def mark_sent(self, delivery_id: UUID, *, provider_message_id: str | None = None) -> NotificationDelivery | None:
        return await self.repository.mark_sent(delivery_id, provider_message_id=provider_message_id)

    async def mark_delivered(self, delivery_id: UUID) -> NotificationDelivery | None:
        return await self.repository.mark_delivered(delivery_id)

    async def fail(
        self,
        delivery_id: UUID,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
        provider_response: dict[str, Any] | None = None,
    ) -> NotificationDelivery | None:
        delivery = await self.get(delivery_id)
        if delivery is None:
            return None

        if delivery.attempt_count >= self.MAX_ATTEMPTS:
            return await self.repository.mark_failed(
                delivery_id,
                error_code=error_code,
                error_message=error_message,
            )

        return await self.schedule_retry(
            delivery_id,
            error_code=error_code,
            error_message=error_message,
            provider_response=provider_response,
        )

    async def schedule_retry(
        self,
        delivery_id: UUID,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
        provider_response: dict[str, Any] | None = None,
    ) -> NotificationDelivery | None:
        delivery = await self.get(delivery_id)
        if delivery is None:
            return None
        if delivery.attempt_count >= self.MAX_ATTEMPTS:
            return await self.repository.mark_failed(
                delivery_id,
                error_code=error_code,
                error_message=error_message,
            )

        index = min(max(delivery.attempt_count - 1, 0), len(self.RETRY_DELAYS) - 1)
        next_retry_at = datetime.now(UTC) + timedelta(seconds=self.RETRY_DELAYS[index])
        values: dict[str, Any] = {"next_retry_at": next_retry_at}
        if error_code is not None:
            values["provider_error_code"] = error_code
        if error_message is not None:
            values["last_error"] = error_message
        if provider_response is not None:
            values["provider_response"] = provider_response
        await self.repository.update_delivery(delivery_id, values)
        return await self.repository.mark_retrying(delivery_id, next_retry_at=next_retry_at)

    async def recover_stale(self, *, timeout_seconds: int = 300, limit: int = 100) -> int:
        return await self.repository.recover_stale_processing(
            timeout_seconds=timeout_seconds,
            limit=limit,
        )

    async def set_provider(self, delivery_id: UUID, *, provider: str) -> NotificationDelivery | None:
        return await self.repository.update_delivery(delivery_id, {"provider": provider})

    async def set_provider_message_id(self, delivery_id: UUID, *, provider_message_id: str) -> NotificationDelivery | None:
        return await self.repository.update_delivery(delivery_id, {"provider_message_id": provider_message_id})

    async def count_for_notification(self, notification_id: UUID) -> int:
        return await self.repository.count_notification_deliveries(notification_id)

    async def pending_count(self) -> int:
        return await self.repository.count_pending()

    async def exists(self, delivery_id: UUID) -> bool:
        return await self.repository.delivery_exists(delivery_id)
