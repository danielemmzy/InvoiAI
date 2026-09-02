"""
============================================================
Organization Usage Repository

Responsibilities:
- Monthly usage
- Plan usage
- Usage metrics
- Usage persistence

No business logic.
No authorization.
No FastAPI.
============================================================
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from app.mappers.organization_mapper import OrganizationUsageMapper
from app.models.domain.organization import OrganizationUsage
from app.repositories.base import BaseRepository


class UsageRepository(BaseRepository):
    """
    Repository for public.organization_usage.
    """

    table_name = "organization_usage"
    mapper = OrganizationUsageMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def create_usage(
        self,
        usage: OrganizationUsage | dict,
    ) -> OrganizationUsage | None:
        return await self.create(usage)

    async def get_usage(
        self,
        usage_id: UUID,
    ) -> OrganizationUsage | None:
        return await self.get(usage_id)

    async def update_usage(
        self,
        usage_id: UUID,
        data,
    ) -> OrganizationUsage | None:
        return await self.update(
            usage_id,
            data,
        )

    async def delete_usage(
        self,
        usage_id: UUID,
    ) -> bool:
        return await self.delete(usage_id)

    # =========================================================
    # Current Usage
    # =========================================================

    async def get_current_usage(
        self,
        org_id: UUID,
        month: date,
    ) -> OrganizationUsage | None:
        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("month", month.isoformat())
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def usage_exists(
        self,
        org_id: UUID,
        month: date,
    ) -> bool:
        response = (
            self.table()
            .select("id")
            .eq("org_id", str(org_id))
            .eq("month", month.isoformat())
            .limit(1)
            .execute()
        )

        return bool(response.data)

    # =========================================================
    # Usage History
    # =========================================================

    async def list_org_usage(
        self,
        org_id: UUID,
    ) -> list[OrganizationUsage]:
        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("month", desc=True)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Usage Metrics
    # =========================================================

    async def update_usage_metrics(
        self,
        *,
        org_id: UUID,
        month: date,
        user_id: UUID | None = None,
        document_increment: int = 0,
        storage_increment: int = 0,
        ai_tokens_increment: int = 0,
        api_calls_increment: int = 0,
        ai_cost_increment: Decimal = Decimal("0"),
    ) -> None:
        self.db.rpc(
            "usage_update_metrics",
            {
                "p_org_id": str(org_id),
                "p_month": month.isoformat(),
                "p_document_increment": document_increment,
                "p_storage_increment": storage_increment,
                "p_ai_tokens_increment": ai_tokens_increment,
                "p_api_calls_increment": api_calls_increment,
                "p_ai_cost_increment": str(ai_cost_increment),
                "p_user_id": str(user_id) if user_id else None,
            },
        ).execute()

    # =========================================================
    # Month
    # =========================================================

    @staticmethod
    def current_month() -> date:
        """
        Return the first day of the current UTC month.

        Example:
            2026-08-21 -> date(2026, 8, 1)

        This matches PostgreSQL:
            organization_usage.month DATE
        """

        now = datetime.now(UTC)

        return date(
            now.year,
            now.month,
            1,
        )