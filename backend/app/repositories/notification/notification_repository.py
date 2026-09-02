from __future__ import annotations

from typing import Any
from uuid import UUID

from app.mappers.notification_mapper import NotificationMapper
from app.mappers.notification_preference_mapper import (
    NotificationPreferenceMapper,
)
from app.models.domain.notification import Notification
from app.models.domain.notification_preference import (
    NotificationPreference,
)
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):
    """
    Repository for notifications.
    """

    table_name = "notifications"

    mapper = NotificationMapper

    # =========================================================
    # Notifications
    # =========================================================

    async def create_notification(
        self,
        notification: Notification | dict,
    ) -> Notification | None:

        return await self.create(
            notification,
        )

    async def get_notification(
        self,
        notification_id: UUID,
    ) -> Notification | None:

        return await self.get(
            notification_id,
        )

    async def update_notification(
        self,
        notification_id: UUID,
        values,
    ) -> Notification | None:

        return await self.update(
            notification_id,
            values,
        )

    async def delete_notification(
        self,
        notification_id: UUID,
    ) -> bool:

        return await self.delete(
            notification_id,
        )

    # =========================================================
    # User Notifications
    # =========================================================

    async def list_user_notifications(
        self,
        *,
        user_id: UUID,
        limit: int = 25,
        offset: int = 0,
    ) -> list[Notification]:

        response = (
            self.table()
            .select("*")
            .eq(
                "user_id",
                str(user_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(
            response,
        )

    async def unread_notifications(
        self,
        *,
        user_id: UUID,
    ) -> list[Notification]:

        response = (
            self.table()
            .select("*")
            .eq(
                "user_id",
                str(user_id),
            )
            .eq(
                "is_read",
                False,
            )
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return self._many(
            response,
        )

    async def unread_count(
        self,
        *,
        user_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq(
                "user_id",
                str(user_id),
            )
            .eq(
                "is_read",
                False,
            )
            .execute()
        )

        return response.count or 0

    # =========================================================
    # Read Status
    # =========================================================

    async def mark_as_read(
        self,
        notification_id: UUID,
    ) -> Notification | None:

        return await self.update_notification(
            notification_id,
            {
                "is_read": True,
            },
        )

    async def mark_as_unread(
        self,
        notification_id: UUID,
    ) -> Notification | None:

        return await self.update_notification(
            notification_id,
            {
                "is_read": False,
            },
        )

    async def mark_all_as_read(
        self,
        *,
        user_id: UUID,
    ) -> bool:

        (
            self.table()
            .update(
                {
                    "is_read": True,
                }
            )
            .eq(
                "user_id",
                str(user_id),
            )
            .eq(
                "is_read",
                False,
            )
            .execute()
        )

        return True

    async def exists_with_data_key(
        self,
        *,
        user_id: UUID,
        event_key: str,
    ) -> bool:
        """Return whether an in-app notification with the given idempotency key exists."""
        response = (
            self.table()
            .select("id")
            .eq("user_id", str(user_id))
            .eq("channel", "in_app")
            .contains(
                "data",
                {"finance_event_key": event_key},
            )
            .limit(1)
            .execute()
        )
        return bool(response.data)

    # =========================================================
    # Preferences
    # =========================================================

    async def get_preferences(
        self,
        *,
        user_id: UUID,
    ) -> NotificationPreference | None:

        response = (
            self.db.table(
                "notification_preferences",
            )
            .select("*")
            .eq(
                "user_id",
                str(user_id),
            )
            .limit(1)
            .execute()
        )

        row = self.raw(
            response,
        )

        return NotificationPreferenceMapper.to_domain(
            row,
        )

    async def save_preferences(
        self,
        preference: NotificationPreference | dict,
    ):

        if isinstance(
            preference,
            NotificationPreference,
        ):
            preference = preference.model_dump(
                exclude_none=True,
            )

        existing = await self.get_preferences(
            user_id=preference["user_id"],
        )

        if existing:

            response = (
                self.db.table(
                    "notification_preferences",
                )
                .update(
                    NotificationPreferenceMapper.to_update(
                        preference,
                    )
                )
                .eq(
                    "user_id",
                    str(
                        preference["user_id"],
                    ),
                )
                .execute()
            )

        else:

            response = (
                self.db.table(
                    "notification_preferences",
                )
                .insert(
                    NotificationPreferenceMapper.to_insert(
                        preference,
                    )
                )
                .execute()
            )

        row = self.raw(
            response,
        )

        return NotificationPreferenceMapper.to_domain(
            row,
        )
