"""
============================================================
Organization Settings Repository
============================================================

Persistence boundary for organization_settings.

Legacy database rows are normalized before they reach the
domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.mappers.organization_mapper import (
    OrganizationSettingsMapper,
)
from app.models.domain.organization import (
    OrganizationSettings,
)
from app.repositories.base import BaseRepository


class OrganizationSettingsRepository(
    BaseRepository
):
    table_name = "organization_settings"

    mapper = OrganizationSettingsMapper

    async def create_settings(
        self,
        settings: OrganizationSettings | dict,
    ) -> OrganizationSettings | None:

        if isinstance(settings, dict):
            settings = dict(settings)

            if settings.get("sso_config") is None:
                settings["sso_config"] = {}

        return await self.create(
            settings
        )

    async def get_settings(
        self,
        org_id: UUID,
    ) -> OrganizationSettings | None:

        response = (
            self.table()
            .select("*")
            .eq(
                "org_id",
                str(org_id),
            )
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        row = dict(rows[0])

        # ----------------------------------------------------
        # Legacy data repair
        # ----------------------------------------------------

        if row.get("sso_config") is None:

            self.table().update(
                {
                    "sso_config": {},
                    "updated_at": (
                        datetime.now(
                            UTC
                        ).isoformat()
                    ),
                }
            ).eq(
                "org_id",
                str(org_id),
            ).execute()

            row["sso_config"] = {}

        return self.mapper.to_domain(
            row
        )

    async def update_settings(
        self,
        org_id: UUID,
        data,
    ) -> OrganizationSettings | None:

        if isinstance(data, dict):

            data = dict(data)

            if data.get(
                "sso_config"
            ) is None:
                data["sso_config"] = {}

            data["updated_at"] = (
                datetime.now(
                    UTC
                ).isoformat()
            )

        response = (
            self.table()
            .update(data)
            .eq(
                "org_id",
                str(org_id),
            )
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        row = dict(rows[0])

        if row.get("sso_config") is None:
            row["sso_config"] = {}

        return self.mapper.to_domain(
            row
        )

    async def delete_settings(
        self,
        org_id: UUID,
    ) -> bool:

        response = (
            self.table()
            .delete()
            .eq(
                "org_id",
                str(org_id),
            )
            .execute()
        )

        return bool(
            response.data
        )

    async def settings_exist(
        self,
        org_id: UUID,
    ) -> bool:

        response = (
            self.table()
            .select("id")
            .eq(
                "org_id",
                str(org_id),
            )
            .limit(1)
            .execute()
        )

        return bool(
            response.data
        )