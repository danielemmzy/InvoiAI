from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class NotificationProvider(ABC):
    """
    Abstract notification delivery provider.

    Providers implement transport/delivery only.
    Business rules remain in services.
    """

    channel: str

    @abstractmethod
    async def send(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        organization_id: UUID | None = None,
        recipient: str | None = None,
        template: str | None = None,
    ) -> bool:
        """
        Deliver a notification through this provider.
        """
        raise NotImplementedError

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Return whether the provider is configured and available.
        """
        raise NotImplementedError