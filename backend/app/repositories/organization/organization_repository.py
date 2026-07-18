"""
============================================================
Organization Repository

Handles ONLY database operations.

No business logic.
No authorization.
No FastAPI.
============================================================
"""

from typing import Any

from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository):

    TABLE = "organizations"

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    async def create(self, values: dict[str, Any]) -> dict:

        result = (
            self.db.table(self.TABLE)
            .insert(values)
            .execute()
        )

        return result.data[0]

    # ---------------------------------------------------------
    # Get by ID
    # ---------------------------------------------------------

    async def get_by_id(self, org_id: str) -> dict | None:

        result = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]

    # ---------------------------------------------------------
    # Get by Slug
    # ---------------------------------------------------------

    async def get_by_slug(self, slug: str) -> dict | None:

        result = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]

    # ---------------------------------------------------------
    # Update
    # ---------------------------------------------------------

    async def update(
        self,
        org_id: str,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.db.table(self.TABLE)
            .update(values)
            .eq("id", org_id)
            .execute()
        )

        return result.data[0]

    # ---------------------------------------------------------
    # Delete
    # ---------------------------------------------------------

    async def delete(self, org_id: str) -> None:

        (
            self.db.table(self.TABLE)
            .delete()
            .eq("id", org_id)
            .execute()
        )

    # ---------------------------------------------------------
    # Exists
    # ---------------------------------------------------------

    async def exists(self, org_id: str) -> bool:

        result = (
            self.db.table(self.TABLE)
            .select("id")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)