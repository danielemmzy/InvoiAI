from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any


class BaseWebhookHandler(ABC):
    """
    Base webhook handler.

    Responsibilities
    ----------------
    • Verify webhook authenticity
    • Parse incoming payload
    • Dispatch supported events

    No persistence.

    No provider-specific logic.
    """

    # =====================================================
    # Verification
    # =====================================================

    @abstractmethod
    async def verify(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """
        Verify webhook signature.
        """

    # =====================================================
    # Parsing
    # =====================================================

    @abstractmethod
    async def parse(
        self,
        *,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Convert provider payload into normalized events.
        """

    # =====================================================
    # Processing
    # =====================================================

    @abstractmethod
    async def process(
        self,
        *,
        event: dict[str, Any],
    ) -> None:
        """
        Handle a normalized webhook event.
        """

    # =====================================================
    # Entry Point
    # =====================================================

    async def handle(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
        payload: dict[str, Any],
    ) -> None:
        """
        Verify → Parse → Process.
        """

        valid = await self.verify(
            headers=headers,
            body=body,
        )

        if not valid:
            raise ValueError(
                "Invalid webhook signature."
            )

        events = await self.parse(
            payload=payload,
        )

        for event in events:

            await self.process(
                event=event,
            )