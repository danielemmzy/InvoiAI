"""
============================================================
Insight Repository

Persistence for the `insights` table (Flow 10).
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.mappers.insight_mapper import InsightMapper
from app.repositories.base import BaseRepository


class InsightRepository(BaseRepository):
    table_name = "insights"
    mapper = InsightMapper

    async def bulk_create(self, rows: list[dict]) -> list:
        if not rows:
            return []

        response = self.table().insert(rows).execute()
        return self._many(response)

    async def list_active_for_org(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ):
        now = datetime.now(UTC).isoformat()

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_dismissed", False)
            .gt("expires_at", now)
            .order("severity")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return self._many(response)

    async def dismiss(self, insight_id: UUID):
        return await self.update(insight_id, {"is_dismissed": True})

    async def mark_read(self, insight_id: UUID):
        return await self.update(insight_id, {"is_read": True})

    async def list_critical_for_org(self, org_id: UUID):
        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("severity", "critical")
            .eq("is_dismissed", False)
            .execute()
        )
        return self._many(response)
