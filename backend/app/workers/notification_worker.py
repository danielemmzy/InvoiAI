from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.observability import record_notification
from app.services.notification.notification_delivery_service import NotificationDeliveryService
from app.services.notification.notification_dispatcher import NotificationDispatcher
from app.services.notification.queue.base import NotificationQueue
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class NotificationWorker(BaseWorker):
    """Claims durable deliveries and owns ack/retry/failure transitions."""

    def __init__(
        self,
        *,
        queue: NotificationQueue,
        dispatcher: NotificationDispatcher,
        delivery_service: NotificationDeliveryService,
        batch_size: int = 10,
    ) -> None:
        super().__init__(retries=1)
        self.queue = queue
        self.dispatcher = dispatcher
        self.delivery_service = delivery_service
        self.batch_size = batch_size

    async def run(self, **kwargs: Any) -> dict[str, int]:
        recovered = await self.delivery_service.recover_stale()
        deliveries = await self.queue.claim(limit=self.batch_size)

        result = {"recovered": recovered, "processed": 0, "sent": 0, "retrying": 0, "failed": 0}
        for delivery in deliveries:
            result["processed"] += 1
            delivery_id = UUID(str(delivery["id"]))
            try:
                success = await self.dispatcher.process(delivery=delivery)
            except Exception as exc:
                success = False
                error = str(exc)
            else:
                error = "Notification provider returned failure."

            if success:
                await self.queue.acknowledge(delivery_id=delivery_id)
                record_notification(channel=str(delivery.get("channel", "unknown")), result="success")
                result["sent"] += 1
                continue

            updated = await self.delivery_service.fail(
                delivery_id,
                error_message=error,
            )
            record_notification(channel=str(delivery.get("channel", "unknown")), result="failed")
            if updated and updated.status.value == "failed":
                result["failed"] += 1
            else:
                result["retrying"] += 1

        return result
