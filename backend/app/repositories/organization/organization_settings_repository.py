"""
============================================================
app/repositories/organization/organization_settings_repository.py

Repository for organization settings.

This repository owns persistence for the
organization_settings table.

Business logic belongs in OrganizationService.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.mappers.organization_mapper import OrganizationSettingsMapper
from app.models.domain.organization import OrganizationSettings
from app.repositories.base import BaseRepository


class OrganizationSettingsRepository(BaseRepository):
    """
    Repository for organization_settings.
    """

    table_name = "organization_settings"
    mapper = OrganizationSettingsMapper

    async def create_settings(
        self,
        settings: OrganizationSettings | dict,
    ) -> OrganizationSettings | None:
        return await self.create(settings)

    async def get_settings(
        self,
        org_id: UUID,
    ) -> OrganizationSettings | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def update_settings(
        self,
        org_id: UUID,
        data,
    ) -> OrganizationSettings | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        response = (
            self.table()
            .update(data)
            .eq("org_id", str(org_id))
            .execute()
        )

        return self._one(response)

    async def delete_settings(
        self,
        org_id: UUID,
    ) -> bool:

        response = (
            self.table()
            .delete()
            .eq("org_id", str(org_id))
            .execute()
        )

        return bool(response.data)

    async def settings_exist(
        self,
        org_id: UUID,
    ) -> bool:

        response = (
            self.table()
            .select("id")
            .eq("org_id", str(org_id))
            .limit(1)
            .execute()
        )

        return bool(response.data)