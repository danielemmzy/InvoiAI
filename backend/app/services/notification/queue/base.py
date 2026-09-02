from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any
from uuid import UUID


class NotificationQueue(ABC):
    """
    Provider-agnostic notification queue.

    Responsibilities
    ----------------
    - Enqueue durable notification deliveries.
    - Atomically claim work.
    - Acknowledge successful work.
    - Release failed work for retry.

    The queue does NOT:
    - send notifications
    - select providers
    - render templates
    - contain notification business rules

    Implementations may use:
    - PostgreSQL
    - Redis
    - SQS
    - RabbitMQ
    - Celery
    - another queue backend
    """

    @abstractmethod
    async def enqueue(
        self,
        *,
        delivery_id: UUID,
        payload: dict[str, Any],
    ) -> bool:
        """
        Add a delivery to the durable queue.
        """
        raise NotImplementedError

    @abstractmethod
    async def claim(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Atomically claim queued deliveries.
        """
        raise NotImplementedError

    @abstractmethod
    async def acknowledge(
        self,
        *,
        delivery_id: UUID,
    ) -> bool:
        """
        Mark a processing delivery as successfully sent.
        """
        raise NotImplementedError

    @abstractmethod
    async def release(
        self,
        *,
        delivery_id: UUID,
        error: str | None = None,
    ) -> bool:
        """
        Return a failed delivery to the queue.
        """
        raise NotImplementedError
    @abstractmethod
    async def recover_stale(
        self,
        *,
        timeout_seconds: int = 300,
        limit: int = 100,
    ) -> int:
        """Recover abandoned PROCESSING deliveries."""
        raise NotImplementedError
