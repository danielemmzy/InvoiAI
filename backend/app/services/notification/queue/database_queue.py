from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import UUID

from app.services.notification.queue.base import NotificationQueue


class DatabaseNotificationQueue(NotificationQueue):
    """
    PostgreSQL-backed notification queue.

    notification_deliveries is the durable queue.

    Lifecycle
    ---------

        QUEUED
          |
          v
      PROCESSING
          |
          v
        SENT

    Failed processing:

        PROCESSING
             |
             v
          QUEUED

    Queue claiming is performed by a PostgreSQL RPC using:

        FOR UPDATE SKIP LOCKED

    This prevents multiple NotificationWorkers from claiming
    the same delivery concurrently.
    """

    CLAIM_FUNCTION = "claim_notification_deliveries"

    def __init__(
        self,
        db,
    ) -> None:

        self.db = db

    # =========================================================
    # Enqueue
    # =========================================================

    async def enqueue(
        self,
        *,
        delivery_id: UUID,
        payload: dict[str, Any],
    ) -> bool:
        """Persist the queue payload and make the delivery claimable."""
        response = (
            self.db.table("notification_deliveries")
            .update(
                {
                    "status": "queued",
                    "payload": payload,
                    "queued_at": datetime.now(UTC).isoformat(),
                    "next_retry_at": None,
                }
            )
            .eq("id", str(delivery_id))
            .execute()
        )
        return bool(response.data)

    # =========================================================
    # Claim
    # =========================================================

    async def claim(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Atomically claim queued/retrying deliveries using the DB function."""
        response = self.db.rpc(
            "claim_notification_deliveries",
            {"p_limit": limit},
        ).execute()
        return response.data or []

    # =========================================================
    # Acknowledge
    # =========================================================

    async def acknowledge(
        self,
        *,
        delivery_id: UUID,
    ) -> bool:
        """
        Mark a processing delivery as sent.
        """

        response = (
            self.db.table(
                "notification_deliveries",
            )
            .update(
                {
                    "status": "sent",
                    "sent_at": datetime.now(
                        UTC,
                    ).isoformat(),
                }
            )
            .eq(
                "id",
                str(delivery_id),
            )
            .eq(
                "status",
                "processing",
            )
            .execute()
        )

        return bool(response.data)

    # =========================================================
    # Release
    # =========================================================

    async def release(
        self,
        *,
        delivery_id: UUID,
        error: str | None = None,
    ) -> bool:
        """
        Return a failed processing delivery to queued state.

        Retry policy is handled by the worker/delivery service.
        """

        values: dict[str, Any] = {
            "status": "queued",
            "last_error": error,
            "queued_at": datetime.now(
                UTC,
            ).isoformat(),
        }

        response = (
            self.db.table(
                "notification_deliveries",
            )
            .update(values)
            .eq(
                "id",
                str(delivery_id),
            )
            .eq(
                "status",
                "processing",
            )
            .execute()
        )

        return bool(response.data)

    async def recover_stale(
        self,
        *,
        timeout_seconds: int = 300,
        limit: int = 100,
    ) -> int:
        response = self.db.rpc(
            "recover_stale_notification_deliveries",
            {
                "p_timeout_seconds": timeout_seconds,
                "p_limit": limit,
            },
        ).execute()
        return int(response.data or 0)
