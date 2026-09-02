"""
============================================================
Integration Sync Repository

Persistence for integration_syncs.

Business logic belongs in IntegrationService.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.mappers.integration_mapper import IntegrationSyncMapper
from app.models.domain.integration import IntegrationSync
from app.repositories.base import BaseRepository


class IntegrationSyncRepository(BaseRepository):
    """
    Repository for integration_syncs.
    """

    table_name = "integration_syncs"

    mapper = IntegrationSyncMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def create_sync(
        self,
        sync: IntegrationSync | dict,
    ) -> IntegrationSync | None:
        return await self.create(sync)

    async def get_sync(
        self,
        sync_id: UUID,
    ) -> IntegrationSync | None:
        return await self.get(sync_id)

    async def update_sync(
        self,
        sync_id: UUID,
        data,
    ) -> IntegrationSync | None:
        return await self.update(
            sync_id,
            data,
        )

    async def delete_sync(
        self,
        sync_id: UUID,
    ) -> bool:
        return await self.delete(sync_id)

    # =========================================================
    # Queries
    # =========================================================

    async def list_connection_syncs(
        self,
        connection_id: UUID,
        limit: int = 50,
    ) -> list[IntegrationSync]:

        response = (
            self.table()
            .select("*")
            .eq("connection_id", str(connection_id))
            .order(
                "started_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_org_syncs(
        self,
        org_id: UUID,
        limit: int = 100,
    ) -> list[IntegrationSync]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "started_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def latest_sync(
        self,
        connection_id: UUID,
    ) -> IntegrationSync | None:

        response = (
            self.table()
            .select("*")
            .eq("connection_id", str(connection_id))
            .order(
                "started_at",
                desc=True,
            )
            .limit(1)
            .execute()
        )

        return self._one(response)

    # =========================================================
    # State Updates
    # =========================================================

    async def complete_sync(
        self,
        sync_id: UUID,
        values: dict,
    ) -> IntegrationSync | None:

        values.setdefault(
            "completed_at",
            datetime.now(UTC),
        )

        return await self.update(
            sync_id,
            values,
        )

    async def fail_sync(
        self,
        sync_id: UUID,
        error_details: dict,
    ) -> IntegrationSync | None:

        return await self.update(
            sync_id,
            {
                "status": "failed",
                "error_details": error_details,
                "completed_at": datetime.now(UTC),
            },
        )