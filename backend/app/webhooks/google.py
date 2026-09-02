from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.webhooks.base import BaseWebhookHandler


class GoogleWebhookHandler(BaseWebhookHandler):
    """
    Google webhook handler.

    Responsibilities
    ----------------
    • Verify Google Pub/Sub push requests
    • Normalize Google events
    • Produce provider-independent events

    Supports:
        • Google Drive
        • Google Sheets
        • Gmail
        • Future Google APIs

    No persistence.

    No business logic.
    """

    VERIFICATION_HEADER = "x-goog-channel-token"

    # =====================================================
    # Verify
    # =====================================================

    async def verify(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:

        token = headers.get(
            self.VERIFICATION_HEADER,
        )

        return token == settings.google_webhook_token

    # =====================================================
    # Parse
    # =====================================================

    async def parse(
        self,
        *,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:

        events: list[dict[str, Any]] = []

        #
        # Google Pub/Sub messages
        #

        message = payload.get(
            "message",
        )

        if message:

            events.append(
                {
                    "provider": "google",
                    "message_id": message.get(
                        "messageId",
                    ),
                    "publish_time": message.get(
                        "publishTime",
                    ),
                    "attributes": message.get(
                        "attributes",
                        {},
                    ),
                    "data": message.get(
                        "data",
                    ),
                }
            )

            return events

        #
        # Generic Google event
        #

        events.append(
            {
                "provider": "google",
                "payload": payload,
            }
        )

        return events

    # =====================================================
    # Process
    # =====================================================

    async def process(
        self,
        *,
        event: dict[str, Any],
    ) -> None:
        """
        Processing is delegated later to
        WebhookDispatcher.

        This handler only verifies and
        normalizes webhook events.
        """

        return