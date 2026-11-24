"""
============================================================
Insight Repository

Persistence for the `insights` table (Flow 10).
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi.encoders import jsonable_encoder

from app.mappers.insight_mapper import InsightMapper
from app.repositories.base import BaseRepository
from app.core.db import execute


class InsightRepository(BaseRepository):
    table_name = "insights"
    mapper = InsightMapper

    async def bulk_create(self, rows: list[dict]) -> list:
        if not rows:
            return []

        response = await execute(self.table().insert(jsonable_encoder(rows)))
        return self._many(response)

    async def list_active_for_org(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ):
        now = datetime.now(UTC).isoformat()

        response = await execute(
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_dismissed", False)
            .gt("expires_at", now)
            .order("severity")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        return self._many(response)

    async def dismiss(self, insight_id: UUID):
        return await self.update(insight_id, {"is_dismissed": True})

    async def mark_read(self, insight_id: UUID):
        return await self.update(insight_id, {"is_read": True})

    async def list_critical_for_org(self, org_id: UUID):
        response = await execute(
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("severity", "critical")
            .eq("is_dismissed", False)
        )
        return self._many(response)
