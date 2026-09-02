"""
============================================================
Organization Repository

Persistence layer for organizations.

Responsibilities
----------------
- CRUD operations
- Retrieval by indexed fields
- Organization existence checks

No business logic.
No authorization.
No FastAPI.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import PlanType
from app.mappers.organization_mapper import OrganizationMapper
from app.models.domain.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository):
    """
    Repository for organizations.
    """

    table_name = "organizations"
    mapper = OrganizationMapper

    async def create_organization(
        self,
        organization: Organization | dict,
    ) -> Organization | None:
        return await self.create(organization)

    async def get_organization(
        self,
        org_id: UUID,
    ) -> Organization | None:
        return await self.get(org_id)

    async def update_organization(
        self,
        org_id: UUID,
        data,
    ) -> Organization | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            org_id,
            data,
        )

    async def delete_organization(
        self,
        org_id: UUID,
    ) -> bool:
        return await self.delete(org_id)

    # --------------------------------------------------------

    async def get_by_slug(
        self,
        slug: str,
    ) -> Organization | None:

        response = (
            self.table()
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def get_by_stripe_customer(
        self,
        customer_id: str,
    ) -> Organization | None:

        response = (
            self.table()
            .select("*")
            .eq("stripe_customer_id", customer_id)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_by_plan(
        self,
        plan: PlanType,
    ) -> list[Organization]:

        response = (
            self.table()
            .select("*")
            .eq("plan", plan.value)
            .order("created_at", desc=True)
            .execute()
        )

        return self._many(response)

    # --------------------------------------------------------

    async def update_plan(
        self,
        org_id: UUID,
        plan: PlanType,
    ) -> Organization | None:

        return await self.update_organization(
            org_id,
            {
                "plan": plan.value,
            },
        )

    async def update_document_limit(
        self,
        org_id: UUID,
        limit: int,
    ) -> Organization | None:

        return await self.update_organization(
            org_id,
            {
                "document_limit": limit,
            },
        )

    async def update_features(
        self,
        org_id: UUID,
        features: dict,
    ) -> Organization | None:

        return await self.update_organization(
            org_id,
            {
                "features": features,
            },
        )

    # --------------------------------------------------------

    async def slug_exists(
        self,
        slug: str,
    ) -> bool:

        response = (
            self.table()
            .select("id")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )

        return bool(response.data)

    # =========================================================
    # Analytics
    # =========================================================

    from datetime import UTC, datetime


    async def organization_count(self) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .execute()
        )

        return response.count or 0


    async def active_organizations(self) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("is_active", True)
            .execute()
        )

        return response.count or 0


    async def organizations_by_plan(self) -> dict[str, int]:

        response = (
            self.table()
            .select("plan")
            .execute()
        )

        plans = {
            "free": 0,
            "starter": 0,
            "pro": 0,
            "enterprise": 0,
        }

        for row in response.data or []:

            plan = row.get("plan")

            if plan in plans:
                plans[plan] += 1

        return plans


    async def new_organizations_this_month(self) -> int:

        start = (
            datetime.now(UTC)
            .replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            .isoformat()
        )

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .gte(
                "created_at",
                start,
            )
            .execute()
        )

        return response.count or 0


    async def storage_usage(
        self,
        org_id: UUID,
    ) -> dict:

        response = (
            self.table()
            .select(
                "storage_used_mb,storage_limit_mb"
            )
            .eq("id", str(org_id))
            .single()
            .execute()
        )

        if not response.data:
            return {}

        used = response.data.get(
            "storage_used_mb",
            0,
        )

        limit = response.data.get(
            "storage_limit_mb",
            0,
        )

        percentage = (
            round((used / limit) * 100, 2)
            if limit
            else 0
        )

        return {
            "used_mb": used,
            "limit_mb": limit,
            "remaining_mb": max(limit - used, 0),
            "percentage": percentage,
        }


    async def plan_usage(
        self,
        org_id: UUID,
    ) -> dict:

        response = (
            self.table()
            .select(
                """
                plan,
                document_limit,
                documents_processed,
                storage_limit_mb,
                storage_used_mb
                """
            )
            .eq("id", str(org_id))
            .single()
            .execute()
        )

        if not response.data:
            return {}

        docs = response.data.get(
            "documents_processed",
            0,
        )

        limit = response.data.get(
            "document_limit",
            0,
        )

        storage = response.data.get(
            "storage_used_mb",
            0,
        )

        storage_limit = response.data.get(
            "storage_limit_mb",
            0,
        )

        return {
            "plan": response.data["plan"],
            "documents_used": docs,
            "documents_limit": limit,
            "documents_remaining": max(limit - docs, 0),
            "document_usage_percent": (
                round((docs / limit) * 100, 2)
                if limit
                else 0
            ),
            "storage_used_mb": storage,
            "storage_limit_mb": storage_limit,
            "storage_remaining_mb": max(
                storage_limit - storage,
                0,
            ),
            "storage_usage_percent": (
                round(
                    (storage / storage_limit) * 100,
                    2,
                )
                if storage_limit
                else 0
            ),
        }
    async def list_all_ids(self, *, limit: int = 1000) -> list[UUID]:
        """Return organization IDs for internal scheduler fan-out."""
        response = self.table().select("id").order("created_at").limit(limit).execute()
        return [UUID(str(row["id"])) for row in (response.data or [])]
