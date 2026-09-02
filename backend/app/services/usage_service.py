"""
============================================================
Usage Service

Business logic for organization usage.

Responsibilities
----------------
- Check usage limits
- Record usage
- Return usage summaries

No SQL.
No Supabase.
============================================================
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.repositories.organization.organization_repository import (
    OrganizationRepository,
)
from app.repositories.organization.usage_repository import (
    UsageRepository,
)


class UsageService:
    """
    Organization usage business logic.
    """

    def __init__(
        self,
        usage_repository: UsageRepository,
        organization_repository: OrganizationRepository,
    ):
        self.usage_repository = usage_repository
        self.organization_repository = organization_repository

    # =====================================================
    # Helpers
    # =====================================================

    @staticmethod
    def current_month() -> str:
        return date.today().strftime("%Y-%m")

    # =====================================================
    # Usage Retrieval
    # =====================================================

    async def get_current_usage(
        self,
        org_id: UUID,
    ):
        return await self.usage_repository.get_current_usage(
            org_id,
            self.current_month(),
        )

    async def get_usage_summary(
        self,
        org_id: UUID,
    ) -> dict:

        organization = await (
            self.organization_repository.get_organization(
                org_id,
            )
        )

        if organization is None:
            raise ValueError(
                "Organization not found."
            )

        usage = await self.get_current_usage(
            org_id,
        )

        used = (
            usage.documents_processed
            if usage
            else 0
        )

        limit = organization.document_limit

        return {
            "month": self.current_month(),
            "plan": organization.plan,
            "used": used,
            "limit": limit,
            "remaining": max(
                limit - used,
                0,
            ),
            "limit_reached": used >= limit,
        }

    # =====================================================
    # Limits
    # =====================================================

    async def check_document_limit(
        self,
        org_id: UUID,
    ) -> None:

        summary = await self.get_usage_summary(
            org_id,
        )

        if summary["limit_reached"]:
            raise ValueError(
                "Monthly document limit reached."
            )

    # =====================================================
    # Recording Usage
    # =====================================================

    async def record_document_processed(
        self,
        *,
        org_id: UUID,
        user_id: UUID | None = None,
        storage_bytes: int = 0,
        ai_tokens: int = 0,
        ai_cost: Decimal = Decimal("0"),
    ) -> None:

        await self.usage_repository.update_usage_metrics(
            org_id=org_id,
            month=self.current_month(),
            user_id=user_id,
            document_increment=1,
            storage_increment=storage_bytes,
            ai_tokens_increment=ai_tokens,
            api_calls_increment=0,
            ai_cost_increment=ai_cost,
        )

    async def record_api_call(
        self,
        *,
        org_id: UUID,
        user_id: UUID | None = None,
    ) -> None:

        await self.usage_repository.update_usage_metrics(
            org_id=org_id,
            month=self.current_month(),
            user_id=user_id,
            api_calls_increment=1,
        )

    async def record_ai_request(
        self,
        *,
        org_id: UUID,
        user_id: UUID | None = None,
        tokens: int = 0,
        cost: Decimal = Decimal("0"),
    ) -> None:

        await self.usage_repository.update_usage_metrics(
            org_id=org_id,
            month=self.current_month(),
            user_id=user_id,
            ai_tokens_increment=tokens,
            ai_cost_increment=cost,
        )

    # =====================================================
    # Utilities
    # =====================================================

    async def usage_exists(
        self,
        org_id: UUID,
    ) -> bool:

        return await self.usage_repository.usage_exists(
            org_id,
            self.current_month(),
        )