from uuid import uuid4

from app2.core.enum.notification import NotificationChannel, NotificationDeliveryStatus, NotificationProvider
from app2.mappers.notification_delivery_mapper import NotificationDeliveryMapper
from app2.models.domain.notification_delivery import NotificationDelivery


def test_notification_delivery_round_trip_fields():
    notification_id = uuid4()
    user_id = uuid4()
    delivery = NotificationDelivery(
        notification_id=notification_id,
        user_id=user_id,
        channel=NotificationChannel.EMAIL,
        provider=NotificationProvider.SMTP,
        status=NotificationDeliveryStatus.RETRYING,
        attempt_count=2,
        last_error="temporary smtp failure",
        provider_error_code="421",
        payload={"title": "Test", "message": "Hello"},
    )

    row = NotificationDeliveryMapper.to_insert(delivery)
    assert row["notification_id"] == str(notification_id)
    assert row["channel"] == "email"
    assert row["provider"] == "smtp"
    assert row["status"] == "retrying"
    assert row["attempt_count"] == 2
    assert row["last_error"] == "temporary smtp failure"
    assert row["provider_error_code"] == "421"

    restored = NotificationDeliveryMapper.to_domain(row)
    assert restored is not None
    assert restored.channel is NotificationChannel.EMAIL
    assert restored.provider is NotificationProvider.SMTP
    assert restored.status is NotificationDeliveryStatus.RETRYING
