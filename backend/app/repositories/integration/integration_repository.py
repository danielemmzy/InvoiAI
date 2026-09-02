"""
============================================================
Integration Repository

Persistence for:

- integration_connections
- integration_syncs

Business logic belongs in IntegrationService.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.mappers.integration_mapper import (
    IntegrationConnectionMapper,
    IntegrationSyncMapper,
)
from app.models.domain.integration import (
    IntegrationConnection,
    IntegrationSync,
)
from app.repositories.base import BaseRepository


# ============================================================
# Connection Repository
# ============================================================


class IntegrationConnectionRepository(BaseRepository):
    """
    Repository for integration_connections.
    """

    table_name = "integration_connections"
    mapper = IntegrationConnectionMapper

    async def create_connection(
        self,
        connection: IntegrationConnection | dict,
    ) -> IntegrationConnection | None:
        return await self.create(connection)

    async def get_connection(
        self,
        connection_id: UUID,
    ) -> IntegrationConnection | None:
        return await self.get(connection_id)

    async def update_connection(
        self,
        connection_id: UUID,
        data,
    ) -> IntegrationConnection | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            connection_id,
            data,
        )

    async def delete_connection(
        self,
        connection_id: UUID,
    ) -> bool:
        return await self.delete(connection_id)

    # --------------------------------------------------------

    async def get_org_connection(
        self,
        org_id: UUID,
        provider: IntegrationProvider,
    ) -> IntegrationConnection | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("provider", provider.value)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_org_connections(
        self,
        org_id: UUID,
    ) -> list[IntegrationConnection]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .execute()
        )

        return self._many(response)

    async def list_active_connections(
        self,
        provider: IntegrationProvider,
    ) -> list[IntegrationConnection]:

        response = (
            self.table()
            .select("*")
            .eq("provider", provider.value)
            .eq("is_active", True)
            .eq("sync_enabled", True)
            .execute()
        )

        return self._many(response)

    # --------------------------------------------------------

    async def update_tokens(
        self,
        connection_id: UUID,
        access_token: str,
        refresh_token: str | None,
        expires_at,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            },
        )

    async def activate_connection(
        self,
        connection_id: UUID,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "is_active": True,
            },
        )

    async def deactivate_connection(
        self,
        connection_id: UUID,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "is_active": False,
            },
        )

    async def enable_sync(
        self,
        connection_id: UUID,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "sync_enabled": True,
            },
        )

    async def disable_sync(
        self,
        connection_id: UUID,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "sync_enabled": False,
            },
        )

    async def update_sync_cursor(
        self,
        connection_id: UUID,
        sync_from_date,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "sync_from_date": sync_from_date,
            },
        )

    async def record_error(
        self,
        connection_id: UUID,
        error: str,
        error_count: int,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "last_error": error,
                "last_error_at": datetime.now(UTC),
                "error_count": error_count,
                "health_status": "error",
            },
        )

    async def clear_error(
        self,
        connection_id: UUID,
    ) -> IntegrationConnection | None:

        return await self.update_connection(
            connection_id,
            {
                "last_error": None,
                "last_error_at": None,
                "error_count": 0,
                "health_status": "healthy",
            },
        )

    async def has_active_connection(
        self,
        org_id: UUID,
        provider: IntegrationProvider,
    ) -> bool:

        response = (
            self.table()
            .select("id")
            .eq("org_id", str(org_id))
            .eq("provider", provider.value)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        return bool(response.data)


