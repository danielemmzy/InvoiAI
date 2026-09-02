from uuid import UUID

from app.core.enum.notification import NotificationChannel


def notification_delivery_key(
    *,
    notification_id: UUID,
    channel: NotificationChannel,
) -> str:
    return f"{notification_id}:{channel.value}"