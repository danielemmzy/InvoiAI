"""
============================================================
Integration Repository

Handles external accounting integrations.

Tables:
- integration_connections
- integration_syncs

No business logic.
============================================================
"""

from datetime import UTC, datetime
from typing import Any

from backend.app.core.enum.enums import IntegrationProvider
from app.repositories.base import BaseRepository


class IntegrationRepository(BaseRepository):

    CONNECTION_TABLE = "integration_connections"
    SYNC_TABLE = "integration_syncs"

    def connections(self):
        return self.db.table(self.CONNECTION_TABLE)

    def syncs(self):
        return self.db.table(self.SYNC_TABLE)
    
        # =========================================================
    # Connections
    # =========================================================

    async def create_connection(
        self,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.connections()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_connection(
        self,
        connection_id: str,
    ) -> dict | None:

        result = (
            self.connections()
            .select("*")
            .eq("id", connection_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_org_connection(
        self,
        org_id: str,
        provider: IntegrationProvider,
    ) -> dict | None:
        """
        Uses unique(org_id, provider).
        """

        result = (
            self.connections()
            .select("*")
            .eq("org_id", org_id)
            .eq("provider", provider.value)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_org_connections(
        self,
        org_id: str,
    ) -> list[dict]:

        result = (
            self.connections()
            .select("*")
            .eq("org_id", org_id)
            .execute()
        )

        return result.data or []

    async def list_active_connections(
        self,
        provider: IntegrationProvider,
    ) -> list[dict]:
        """
        Uses idx_conn_active.
        """

        result = (
            self.connections()
            .select("*")
            .eq("provider", provider.value)
            .eq("is_active", True)
            .eq("sync_enabled", True)
            .execute()
        )

        return result.data or []
    
        # =========================================================
    # Connection Updates
    # =========================================================

    async def update_connection(
        self,
        connection_id: str,
        values: dict[str, Any],
    ) -> dict:
        """
        Internal update helper.
        """

        values["updated_at"] = datetime.now(UTC)

        result = (
            self.connections()
            .update(values)
            .eq("id", connection_id)
            .execute()
        )

        return result.data[0]

    async def update_tokens(
        self,
        connection_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> dict:
        """
        Update OAuth tokens after a refresh.
        """

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
        connection_id: str,
    ) -> dict:
        """
        Mark an integration as active.
        """

        return await self.update_connection(
            connection_id,
            {
                "is_active": True,
            },
        )

    async def deactivate_connection(
        self,
        connection_id: str,
    ) -> dict:
        """
        Disable an integration.
        """

        return await self.update_connection(
            connection_id,
            {
                "is_active": False,
            },
        )

    async def enable_sync(
        self,
        connection_id: str,
    ) -> dict:
        """
        Enable automatic synchronization.
        """

        return await self.update_connection(
            connection_id,
            {
                "sync_enabled": True,
            },
        )

    async def disable_sync(
        self,
        connection_id: str,
    ) -> dict:
        """
        Disable automatic synchronization.
        """

        return await self.update_connection(
            connection_id,
            {
                "sync_enabled": False,
            },
        )

    async def update_sync_cursor(
        self,
        connection_id: str,
        sync_from_date,
    ) -> dict:
        """
        Update the synchronization cursor.
        """

        return await self.update_connection(
            connection_id,
            {
                "sync_from_date": sync_from_date,
            },
        )

    async def record_error(
        self,
        connection_id: str,
        error: str,
        error_count: int,
    ) -> dict:
        """
        Store the latest integration error.
        """

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
        connection_id: str,
    ) -> dict:
        """
        Clear the latest integration error.
        """

        return await self.update_connection(
            connection_id,
            {
                "last_error": None,
                "last_error_at": None,
                "error_count": 0,
                "health_status": "healthy",
            },
        )
    
        # =========================================================
    # Sync History
    # =========================================================

    async def create_sync(
        self,
        values: dict[str, Any],
    ) -> dict:
        """
        Create a sync record.
        """

        result = (
            self.syncs()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_sync(
        self,
        sync_id: str,
    ) -> dict | None:
        """
        Get a sync by ID.
        """

        result = (
            self.syncs()
            .select("*")
            .eq("id", sync_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_connection_syncs(
        self,
        connection_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        List sync history for a connection.

        Uses idx_syncs_conn.
        """

        result = (
            self.syncs()
            .select("*")
            .eq("connection_id", connection_id)
            .order(
                "started_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []

    async def list_org_syncs(
        self,
        org_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        List organization sync history.

        Uses idx_syncs_org.
        """

        result = (
            self.syncs()
            .select("*")
            .eq("org_id", org_id)
            .order(
                "started_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []

    async def complete_sync(
        self,
        sync_id: str,
        values: dict[str, Any],
    ) -> dict:
        """
        Complete a sync operation.

        The caller provides fields such as:
        - status
        - cursor_after
        - documents_created
        - documents_updated
        - documents_failed
        - completed_at
        - duration_ms
        """

        values.setdefault(
            "completed_at",
            datetime.now(UTC),
        )

        result = (
            self.syncs()
            .update(values)
            .eq("id", sync_id)
            .execute()
        )

        return result.data[0]

    async def fail_sync(
        self,
        sync_id: str,
        error_details: dict[str, Any],
    ) -> dict:
        """
        Mark a sync as failed.
        """

        result = (
            self.syncs()
            .update(
                {
                    "status": "failed",
                    "error_details": error_details,
                    "completed_at": datetime.now(UTC),
                }
            )
            .eq("id", sync_id)
            .execute()
        )

        return result.data[0]
    
        # =========================================================
    # Helpers
    # =========================================================

    async def connection_exists(
        self,
        connection_id: str,
    ) -> bool:
        """
        Check whether an integration connection exists.
        """

        result = (
            self.connections()
            .select("id")
            .eq("id", connection_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def sync_exists(
        self,
        sync_id: str,
    ) -> bool:
        """
        Check whether a sync exists.
        """

        result = (
            self.syncs()
            .select("id")
            .eq("id", sync_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def has_active_connection(
        self,
        org_id: str,
        provider: IntegrationProvider,
    ) -> bool:
        """
        Check whether an organization has an active connection
        for a provider.
        """

        result = (
            self.connections()
            .select("id")
            .eq("org_id", org_id)
            .eq("provider", provider.value)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def latest_sync(
        self,
        connection_id: str,
    ) -> dict | None:
        """
        Return the most recent sync for a connection.
        """

        result = (
            self.syncs()
            .select("*")
            .eq("connection_id", connection_id)
            .order(
                "started_at",
                desc=True,
            )
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def delete_connection(
        self,
        connection_id: str,
    ) -> None:
        """
        Delete an integration connection.
        """

        (
            self.connections()
            .delete()
            .eq("id", connection_id)
            .execute()
        )