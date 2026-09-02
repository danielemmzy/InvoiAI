from __future__ import annotations

from app.core.enum.notification import NotificationChannel, NotificationDeliveryStatus, NotificationProvider
from app.mappers.base import BaseMapper
from app.models.domain.notification_delivery import NotificationDelivery
from app.services.notification.idempotency import notification_delivery_key


class NotificationDeliveryMapper(BaseMapper):
    """Maps notification_deliveries rows to/from the V2 domain model."""

    domain_model = NotificationDelivery

    @classmethod
    def to_domain(cls, data: dict | None) -> NotificationDelivery | None:
        if not data:
            return None

        provider = data.get("provider") or NotificationProvider.IN_APP.value
        return NotificationDelivery(
            id=data.get("id"),
            notification_id=data["notification_id"],
            user_id=data["user_id"],
            organization_id=data.get("organization_id"),
            channel=data["channel"],
            provider=provider,
            status=data.get("status", NotificationDeliveryStatus.QUEUED.value),
            idempotency_key=data.get("idempotency_key"),
            recipient=data.get("recipient"),
            attempt_count=data.get("attempt_count", data.get("attempts", 0)),
            last_attempt_at=data.get("last_attempt_at"),
            last_error=data.get("last_error", data.get("error_message")),
            failed_at=data.get("failed_at"),
            provider_message_id=data.get("provider_message_id"),
            provider_error_code=data.get("provider_error_code", data.get("error_code")),
            provider_response=data.get("provider_response") or {},
            next_retry_at=data.get("next_retry_at"),
            queued_at=data.get("queued_at"),
            processing_started_at=data.get("processing_started_at"),
            sent_at=data.get("sent_at"),
            delivered_at=data.get("delivered_at"),
            payload=data.get("payload") or {},
            metadata=data.get("metadata") or {},
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @classmethod
    def to_insert(cls, delivery: NotificationDelivery | dict) -> dict:
        if isinstance(delivery, NotificationDelivery):
            delivery = delivery.model_dump(exclude_none=True, mode="json")

        notification_id = delivery["notification_id"]
        channel = delivery["channel"]
        if not isinstance(channel, NotificationChannel):
            channel = NotificationChannel(channel)

        provider = delivery.get("provider", NotificationProvider.IN_APP)
        if isinstance(provider, NotificationProvider):
            provider = provider.value

        status = delivery.get("status", NotificationDeliveryStatus.QUEUED)
        if isinstance(status, NotificationDeliveryStatus):
            status = status.value

        return {
            "notification_id": notification_id,
            "user_id": delivery["user_id"],
            "organization_id": delivery.get("organization_id"),
            "channel": channel.value,
            "provider": provider,
            "status": status,
            "idempotency_key": delivery.get("idempotency_key") or notification_delivery_key(
                notification_id=notification_id,
                channel=channel,
            ),
            "recipient": delivery.get("recipient"),
            "attempt_count": delivery.get("attempt_count", 0),
            "last_attempt_at": delivery.get("last_attempt_at"),
            "last_error": delivery.get("last_error"),
            "failed_at": delivery.get("failed_at"),
            "provider_message_id": delivery.get("provider_message_id"),
            "provider_error_code": delivery.get("provider_error_code"),
            "provider_response": delivery.get("provider_response", {}),
            "next_retry_at": delivery.get("next_retry_at"),
            "queued_at": delivery.get("queued_at"),
            "processing_started_at": delivery.get("processing_started_at"),
            "sent_at": delivery.get("sent_at"),
            "delivered_at": delivery.get("delivered_at"),
            "payload": delivery.get("payload", {}),
            "metadata": delivery.get("metadata", {}),
        }

    @classmethod
    def to_update(cls, delivery: NotificationDelivery | dict) -> dict:
        if isinstance(delivery, NotificationDelivery):
            delivery = delivery.model_dump(exclude_none=True, mode="json")

        immutable = {"id", "notification_id", "user_id", "organization_id", "created_at"}
        payload = {}
        for key, value in delivery.items():
            if key in immutable:
                continue
            if hasattr(value, "value"):
                value = value.value
            payload[key] = value
        return payload
