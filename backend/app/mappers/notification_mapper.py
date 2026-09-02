from __future__ import annotations

from app.mappers.base import BaseMapper
from app.models.domain.notification import Notification


class NotificationMapper(BaseMapper):
    """
    Maps notification database rows to domain models.
    """

    domain_model = Notification

    @classmethod
    def to_domain(
        cls,
        data: dict | None,
    ) -> Notification | None:

        if not data:
            return None

        return Notification(
            id=data.get("id"),
            user_id=data.get("user_id"),
            organization_id=data.get("organization_id"),
            type=data.get("type"),
            title=data.get("title"),
            message=data.get("message"),
            data=data.get("data") or {},
            channel=data.get("channel", "in_app"),
            is_read=data.get("is_read", False),
            read_at=data.get("read_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @classmethod
    def to_insert(
        cls,
        notification: Notification | dict,
    ) -> dict:

        if isinstance(notification, Notification):
            notification = notification.model_dump(
                exclude_none=True,
            )

        return {
            "user_id": notification["user_id"],
            "organization_id": notification.get("organization_id"),
            "type": notification["type"],
            "title": notification["title"],
            "message": notification["message"],
            "data": notification.get("data", {}),
            "channel": notification.get(
                "channel",
                "in_app",
            ),
            "is_read": notification.get(
                "is_read",
                False,
            ),
            "read_at": notification.get("read_at"),
        }

    @classmethod
    def to_update(
        cls,
        notification: Notification | dict,
    ) -> dict:

        if isinstance(notification, Notification):
            notification = notification.model_dump(
                exclude_none=True,
            )

        return {
            k: v
            for k, v in notification.items()
            if k
            not in {
                "id",
                "created_at",
            }
        }