"""
============================================================
app/repositories/organization/organization_settings_repository.py

Repository for organization settings.

This repository owns persistence for the
organization_settings table.

Business logic belongs in OrganizationService.
============================================================
"""

from datetime import UTC, datetime
from typing import Any

from app.repositories.base import BaseRepository


class OrganizationSettingsRepository(BaseRepository):
    """
    Repository for organization settings.
    """

    TABLE = "organization_settings"

    def table(self):
        return self.db.table(self.TABLE)

    # ========================================================
    # Retrieval
    # ========================================================

    async def get_settings(
        self,
        org_id: str,
    ):
        """
        Retrieve organization settings.
        """

        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .single()
            .execute()
        )

    # ========================================================
    # Updates
    # ========================================================

    async def update_settings(
        self,
        org_id: str,
        values: dict[str, Any],
    ):
        """
        Update organization settings.
        """

        values["updated_at"] = datetime.now(UTC)

        return (
            self.table()
            .update(values)
            .eq("org_id", org_id)
            .execute()
        )