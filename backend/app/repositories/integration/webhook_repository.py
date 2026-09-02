"""
============================================================
Webhook Repository

Persistence for integration_webhooks.

Business logic belongs in IntegrationService.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.mappers.integration_mapper import IntegrationWebhookMapper
from app.models.domain.integration import IntegrationWebhook
from app.repositories.base import BaseRepository


class WebhookRepository(BaseRepository):
    """
    Repository for integration_webhooks.
    """

    table_name = "integration_webhooks"

    mapper = IntegrationWebhookMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def create_webhook(
        self,
        webhook: IntegrationWebhook | dict,
    ) -> IntegrationWebhook | None:
        return await self.create(webhook)

    async def get_webhook(
        self,
        webhook_id: UUID,
    ) -> IntegrationWebhook | None:
        return await self.get(webhook_id)

    async def update_webhook(
        self,
        webhook_id: UUID,
        data,
    ) -> IntegrationWebhook | None:
        return await self.update(
            webhook_id,
            data,
        )

    async def delete_webhook(
        self,
        webhook_id: UUID,
    ) -> bool:
        return await self.delete(webhook_id)

    # =========================================================
    # Queries
    # =========================================================

    async def get_provider_event(
        self,
        provider: IntegrationProvider,
        event_id: str,
    ) -> IntegrationWebhook | None:

        response = (
            self.table()
            .select("*")
            .eq("provider", provider.value)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_org_webhooks(
        self,
        org_id: UUID,
        limit: int = 100,
    ) -> list[IntegrationWebhook]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "received_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_unprocessed(
        self,
        provider: IntegrationProvider,
    ) -> list[IntegrationWebhook]:

        response = (
            self.table()
            .select("*")
            .eq("provider", provider.value)
            .eq("processed", False)
            .order("received_at")
            .execute()
        )

        return self._many(response)

    # =========================================================
    # State Updates
    # =========================================================

    async def mark_processed(
        self,
        webhook_id: UUID,
        document_id: UUID | None = None,
    ) -> IntegrationWebhook | None:

        values = {
            "processed": True,
            "processed_at": datetime.now(UTC),
        }

        if document_id:
            values["document_id"] = str(document_id)

        return await self.update(
            webhook_id,
            values,
        )

    async def record_error(
        self,
        webhook_id: UUID,
        error: str,
    ) -> IntegrationWebhook | None:

        return await self.update(
            webhook_id,
            {
                "error": error,
            },
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def event_exists(
        self,
        provider: IntegrationProvider,
        event_id: str,
    ) -> bool:

        response = (
            self.table()
            .select("id")
            .eq("provider", provider.value)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )

        return bool(response.data)