from __future__ import annotations

import hashlib
import hmac
from typing import Any

from app.core.config import settings
from app.webhooks.base import BaseWebhookHandler


class QuickBooksWebhookHandler(BaseWebhookHandler):
    """
    QuickBooks webhook handler.

    Responsibilities
    ----------------
    • Verify Intuit webhook signature
    • Normalize webhook payload
    • Return provider-independent events

    No database.

    No repositories.

    No business logic.
    """

    SIGNATURE_HEADER = "intuit-signature"

    # =====================================================
    # Verify
    # =====================================================

    async def verify(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:

        signature = headers.get(
            self.SIGNATURE_HEADER,
        )

        if not signature:
            return False

        digest = hmac.new(
            settings.quickbooks_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).digest()

        expected = digest.hex()

        return hmac.compare_digest(
            expected,
            signature,
        )

    # =====================================================
    # Parse
    # =====================================================

    async def parse(
        self,
        *,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:

        events: list[dict[str, Any]] = []

        for notification in payload.get(
            "eventNotifications",
            [],
        ):

            realm_id = notification.get(
                "realmId",
            )

            for entity in notification.get(
                "dataChangeEvent",
                {},
            ).get(
                "entities",
                [],
            ):

                events.append(
                    {
                        "provider": "quickbooks",
                        "realm_id": realm_id,
                        "entity": entity.get("name"),
                        "operation": entity.get("operation"),
                        "external_id": entity.get("id"),
                        "last_updated": entity.get(
                            "lastUpdated",
                        ),
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

        This class only normalizes events.
        """

        return