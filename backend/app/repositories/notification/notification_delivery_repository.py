from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.enum.notification import (
    NotificationChannel,
    NotificationDeliveryStatus,
)
from app.mappers.notification_delivery_mapper import (
    NotificationDeliveryMapper,
)
from app.models.domain.notification_delivery import (
    NotificationDelivery,
)
from app.repositories.base import BaseRepository


class NotificationDeliveryRepository(BaseRepository):
    """
    Repository for notification_deliveries.

    Persistence only.
    No notification business logic.
    """

    table_name = "notification_deliveries"

    mapper = NotificationDeliveryMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def create_delivery(
        self,
        delivery: NotificationDelivery | dict,
    ) -> NotificationDelivery | None:

        return await self.create(
            delivery,
        )

    async def get_delivery(
        self,
        delivery_id: UUID,
    ) -> NotificationDelivery | None:

        return await self.get(
            delivery_id,
        )

    async def update_delivery(
        self,
        delivery_id: UUID,
        values: dict,
    ) -> NotificationDelivery | None:

        values = dict(values)

        values["updated_at"] = datetime.now(UTC)

        return await self.update(
            delivery_id,
            values,
        )

    async def delete_delivery(
        self,
        delivery_id: UUID,
    ) -> bool:

        return await self.delete(
            delivery_id,
        )

    # =========================================================
    # Notification Deliveries
    # =========================================================

    async def list_notification_deliveries(
        self,
        *,
        notification_id: UUID,
    ) -> list[NotificationDelivery]:

        response = (
            self.table()
            .select("*")
            .eq(
                "notification_id",
                str(notification_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .order(
                "id",
                desc=True,
            )
            .execute()
        )

        return self._many(response)

    # =========================================================
    # User Deliveries
    # =========================================================

    async def list_user_deliveries(
        self,
        *,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationDelivery]:

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
            .order(
                "id",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Organization Deliveries
    # =========================================================

    async def list_organization_deliveries(
        self,
        *,
        organization_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationDelivery]:

        response = (
            self.table()
            .select("*")
            .eq(
                "organization_id",
                str(organization_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .order(
                "id",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Queue
    # =========================================================

    async def list_queued(
        self,
        *,
        limit: int = 100,
    ) -> list[NotificationDelivery]:

        response = (
            self.table()
            .select("*")
            .in_(
                "status",
                [
                    NotificationDeliveryStatus.QUEUED.value,
                    NotificationDeliveryStatus.RETRYING.value,
                ],
            )
            .or_(
                "next_retry_at.is.null,"
                f"next_retry_at.lte.{datetime.now(UTC).isoformat()}"
            )
            .order(
                "created_at",
            )
            .order(
                "id",
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Status
    # =========================================================

    async def update_status(
        self,
        delivery_id: UUID,
        status: NotificationDeliveryStatus,
    ) -> NotificationDelivery | None:

        return await self.update_delivery(
            delivery_id,
            {
                "status": status.value,
            },
        )

    async def mark_processing(
        self,
        delivery_id: UUID,
    ) -> NotificationDelivery | None:

        return await self.update_status(
            delivery_id,
            NotificationDeliveryStatus.PROCESSING,
        )

    async def mark_sent(
        self,
        delivery_id: UUID,
        *,
        provider_message_id: str | None = None,
    ) -> NotificationDelivery | None:

        values = {
            "status": NotificationDeliveryStatus.SENT.value,
            "sent_at": datetime.now(UTC),
        }

        if provider_message_id is not None:
            values["provider_message_id"] = (
                provider_message_id
            )

        return await self.update_delivery(
            delivery_id,
            values,
        )

    async def mark_delivered(
        self,
        delivery_id: UUID,
    ) -> NotificationDelivery | None:

        return await self.update_delivery(
            delivery_id,
            {
                "status": (
                    NotificationDeliveryStatus.DELIVERED.value
                ),
                "delivered_at": datetime.now(UTC),
            },
        )

    async def mark_failed(
        self,
        delivery_id: UUID,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> NotificationDelivery | None:

        values = {
            "status": NotificationDeliveryStatus.FAILED.value,
            "failed_at": datetime.now(UTC),
        }

        if error_code is not None:
            values["provider_error_code"] = error_code

        if error_message is not None:
            values["last_error"] = error_message

        return await self.update_delivery(
            delivery_id,
            values,
        )

    async def mark_retrying(
        self,
        delivery_id: UUID,
        *,
        next_retry_at: datetime,
    ) -> NotificationDelivery | None:

        return await self.update_delivery(
            delivery_id,
            {
                "status": NotificationDeliveryStatus.RETRYING.value,
                "next_retry_at": next_retry_at,
                "last_error": None,
            },
        )

    # =========================================================
    # Attempts
    # =========================================================

    async def increment_attempt(
        self,
        delivery_id: UUID,
    ) -> NotificationDelivery | None:

        delivery = await self.get_delivery(
            delivery_id,
        )

        if delivery is None:
            return None

        return await self.update_delivery(
            delivery_id,
            {
                "attempt_count": delivery.attempt_count + 1,
                "last_attempt_at": datetime.now(UTC),
            },
        )

    # =========================================================
    # Queries
    # =========================================================

    async def get_by_provider_message_id(
        self,
        *,
        provider: str,
        provider_message_id: str,
    ) -> NotificationDelivery | None:

        response = (
            self.table()
            .select("*")
            .eq(
                "provider",
                provider,
            )
            .eq(
                "provider_message_id",
                provider_message_id,
            )
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def get_channel_delivery(
        self,
        *,
        notification_id: UUID,
        channel: NotificationChannel,
    ) -> NotificationDelivery | None:

        response = (
            self.table()
            .select("*")
            .eq(
                "notification_id",
                str(notification_id),
            )
            .eq(
                "channel",
                channel.value,
            )
            .limit(1)
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Recovery
    # =========================================================

    async def recover_stale_processing(
        self,
        *,
        timeout_seconds: int = 300,
        limit: int = 100,
    ) -> int:
        """Atomically recover abandoned PROCESSING deliveries."""

        response = self.db.rpc(
            "recover_stale_notification_deliveries",
            {
                "p_timeout_seconds": timeout_seconds,
                "p_limit": limit,
            },
        ).execute()
        return int(response.data or 0)

    # =========================================================
    # Counts
    # =========================================================

    async def count_notification_deliveries(
        self,
        notification_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq(
                "notification_id",
                str(notification_id),
            )
            .execute()
        )

        return response.count or 0

    async def count_pending(
        self,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .in_(
                "status",
                [
                    NotificationDeliveryStatus.QUEUED.value,
                    NotificationDeliveryStatus.RETRYING.value,
                ],
            )
            .execute()
        )

        return response.count or 0

    # =========================================================
    # Existence
    # =========================================================

    async def delivery_exists(
        self,
        delivery_id: UUID,
    ) -> bool:

        return await self.exists(
            "id",
            delivery_id,
        )

    async def get_by_idempotency_key(
    self,
    idempotency_key: str,
) -> NotificationDelivery | None:

        response = (
            self.table()
            .select("*")
            .eq(
                "idempotency_key",
                idempotency_key,
            )
            .limit(1)
            .execute()
        )

        return self._one(response)