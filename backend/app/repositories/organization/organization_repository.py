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

from datetime import UTC, datetime
from typing import Any

from backend.app.core.enum.enums import PlanType
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository):
    """
    Repository for the organizations table.
    """

    TABLE = "organizations"

    def table(self):
        return self.db.table(self.TABLE)

    # =========================================================
    # Creation
    # =========================================================

    async def create_organization(
        self,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.table()
            .insert(values)
            .execute()
        )

        return result.data[0]

    # =========================================================
    # Retrieval
    # =========================================================

    async def get_by_id(
        self,
        org_id: str,
    ) -> dict | None:

        result = (
            self.table()
            .select("*")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_by_slug(
        self,
        slug: str,
    ) -> dict | None:

        result = (
            self.table()
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_by_stripe_customer(
        self,
        customer_id: str,
    ) -> dict | None:

        result = (
            self.table()
            .select("*")
            .eq("stripe_customer_id", customer_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_by_plan(
        self,
        plan: PlanType,
    ) -> list[dict]:

        result = (
            self.table()
            .select("*")
            .eq("plan", plan.value)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []

    # =========================================================
    # Updates
    # =========================================================

    async def update_organization(
        self,
        org_id: str,
        values: dict[str, Any],
    ) -> dict:

        values["updated_at"] = datetime.now(UTC)

        result = (
            self.table()
            .update(values)
            .eq("id", org_id)
            .execute()
        )

        return result.data[0]

    async def update_plan(
        self,
        org_id: str,
        plan: PlanType,
    ) -> dict:

        return await self.update_organization(
            org_id,
            {
                "plan": plan.value,
            },
        )

    async def update_document_limit(
        self,
        org_id: str,
        limit: int,
    ) -> dict:

        return await self.update_organization(
            org_id,
            {
                "document_limit": limit,
            },
        )

    async def update_features(
        self,
        org_id: str,
        features: dict[str, Any],
    ) -> dict:

        return await self.update_organization(
            org_id,
            {
                "features": features,
            },
        )

    # =========================================================
    # Deletion
    # =========================================================

    async def delete_organization(
        self,
        org_id: str,
    ) -> None:

        (
            self.table()
            .delete()
            .eq("id", org_id)
            .execute()
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def organization_exists(
        self,
        org_id: str,
    ) -> bool:

        result = (
            self.table()
            .select("id")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def slug_exists(
        self,
        slug: str,
    ) -> bool:

        result = (
            self.table()
            .select("id")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )

        return bool(result.data)