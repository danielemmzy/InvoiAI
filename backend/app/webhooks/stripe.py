from __future__ import annotations

import hmac
from typing import Any

import stripe

from app.core.config import settings
from app.webhooks.base import BaseWebhookHandler


class StripeWebhookHandler(BaseWebhookHandler):
    """
    Stripe webhook handler.

    Responsibilities
    ----------------
    • Verify Stripe webhook signature
    • Normalize Stripe events
    • Produce provider-independent events

    No persistence.

    No business logic.
    """

    SIGNATURE_HEADER = "stripe-signature"

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

        try:

            stripe.Webhook.construct_event(
                payload=body,
                sig_header=signature,
                secret=settings.stripe_webhook_secret,
            )

            return True

        except stripe.error.SignatureVerificationError:

            return False

    # =====================================================
    # Parse
    # =====================================================

    async def parse(
        self,
        *,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:

        event = payload

        return [
            {
                "provider": "stripe",
                "event_id": event.get("id"),
                "event_type": event.get("type"),
                "created": event.get("created"),
                "object": event.get(
                    "data",
                    {},
                ).get(
                    "object",
                    {},
                ),
            }
        ]

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