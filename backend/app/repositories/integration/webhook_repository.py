"""
============================================================
Webhook Repository

Handles webhook persistence.

Table:
- integration_webhooks

No business logic.
============================================================
"""

from datetime import UTC, datetime
from typing import Any

from backend.app.core.enum.enums import IntegrationProvider
from app.repositories.base import BaseRepository


class WebhookRepository(BaseRepository):

    TABLE = "integration_webhooks"

    def webhooks(self):
        return self.db.table(self.TABLE)
    
        # =========================================================
    # Create
    # =========================================================

    async def create_webhook(
        self,
        values: dict[str, Any],
    ) -> dict:
        """
        Store an incoming webhook.
        """

        result = (
            self.webhooks()
            .insert(values)
            .execute()
        )

        return result.data[0]

    # =========================================================
    # Get
    # =========================================================

    async def get_webhook(
        self,
        webhook_id: str,
    ) -> dict | None:
        """
        Get webhook by ID.
        """

        result = (
            self.webhooks()
            .select("*")
            .eq("id", webhook_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_provider_event(
        self,
        provider: IntegrationProvider,
        event_id: str,
    ) -> dict | None:
        """
        Uses unique(provider, event_id).
        """

        result = (
            self.webhooks()
            .select("*")
            .eq("provider", provider.value)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_org_webhooks(
        self,
        org_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Uses idx_webhooks_org.
        """

        result = (
            self.webhooks()
            .select("*")
            .eq("org_id", org_id)
            .order(
                "received_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []
    
        # =========================================================
    # Processing
    # =========================================================

    async def list_unprocessed(
        self,
        provider: IntegrationProvider,
    ) -> list[dict]:
        """
        Uses idx_webhooks_unprocessed.
        """

        result = (
            self.webhooks()
            .select("*")
            .eq("provider", provider.value)
            .eq("processed", False)
            .order("received_at")
            .execute()
        )

        return result.data or []

    async def mark_processed(
        self,
        webhook_id: str,
        document_id: str | None = None,
    ) -> dict:
        """
        Mark webhook as processed.
        """

        values = {
            "processed": True,
            "processed_at": datetime.now(UTC),
        }

        if document_id is not None:
            values["document_id"] = document_id

        result = (
            self.webhooks()
            .update(values)
            .eq("id", webhook_id)
            .execute()
        )

        return result.data[0]

    async def record_error(
        self,
        webhook_id: str,
        error: str,
    ) -> dict:
        """
        Store webhook processing error.
        """

        result = (
            self.webhooks()
            .update(
                {
                    "error": error,
                }
            )
            .eq("id", webhook_id)
            .execute()
        )

        return result.data[0]
    
        # =========================================================
    # Helpers
    # =========================================================

    async def webhook_exists(
        self,
        webhook_id: str,
    ) -> bool:

        result = (
            self.webhooks()
            .select("id")
            .eq("id", webhook_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def event_exists(
        self,
        provider: IntegrationProvider,
        event_id: str,
    ) -> bool:
        """
        Prevent duplicate webhook processing.
        """

        result = (
            self.webhooks()
            .select("id")
            .eq("provider", provider.value)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)