from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

from app.core.config import settings
from app.webhooks.base import BaseWebhookHandler


class XeroWebhookHandler(BaseWebhookHandler):
    """
    Xero webhook handler.

    Responsibilities
    ----------------
    • Verify Xero webhook signature
    • Normalize webhook payload
    • Produce provider-independent events

    No persistence.

    No business logic.
    """

    SIGNATURE_HEADER = "x-xero-signature"

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
            settings.xero_webhook_key.encode(),
            body,
            hashlib.sha256,
        ).digest()

        expected = base64.b64encode(
            digest,
        ).decode()

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

        for item in payload.get(
            "events",
            [],
        ):

            events.append(
                {
                    "provider": "xero",
                    "tenant_id": payload.get(
                        "tenantId",
                    ),
                    "resource": item.get(
                        "resourceType",
                    ),
                    "event_type": item.get(
                        "eventType",
                    ),
                    "event_id": item.get(
                        "eventId",
                    ),
                    "resource_id": item.get(
                        "resourceId",
                    ),
                    "timestamp": item.get(
                        "eventDateUtc",
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

        This handler only verifies and
        normalizes webhook events.
        """

        return