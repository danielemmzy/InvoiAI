"""
============================================================
Organization Member Repository

Handles ONLY organization membership persistence.

Responsibilities:
- Organization memberships
- User roles
- Invitations
- Membership lookup

No business logic.
No authorization.
No FastAPI.
============================================================
"""

from typing import Any

from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository):

    TABLE = "org_members"

    # ---------------------------------------------------------
    # Create Membership
    # ---------------------------------------------------------

    async def create(self, values: dict[str, Any]) -> dict:

        result = (
            self.db.table(self.TABLE)
            .insert(values)
            .execute()
        )

        return result.data[0]

    # ---------------------------------------------------------
    # Get Membership
    # ---------------------------------------------------------

    async def get(
        self,
        org_id: str,
        user_id: str,
    ) -> dict | None:

        result = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]

    # ---------------------------------------------------------
    # Get User Organizations
    # ---------------------------------------------------------

    async def get_user_memberships(
        self,
        user_id: str,
    ) -> list[dict]:

        result = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )

        return result.data

    # ---------------------------------------------------------
    # Get Organization Members
    # ---------------------------------------------------------

    async def get_org_members(
        self,
        org_id: str,
    ) -> list[dict]:

        result = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("org_id", org_id)
            .eq("is_active", True)
            .execute()
        )

        return result.data

    # ---------------------------------------------------------
    # Update Membership
    # ---------------------------------------------------------

    async def update(
        self,
        member_id: str,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.db.table(self.TABLE)
            .update(values)
            .eq("id", member_id)
            .execute()
        )

        return result.data[0]

    # ---------------------------------------------------------
    # Deactivate Membership
    # ---------------------------------------------------------

    async def deactivate(
        self,
        member_id: str,
    ) -> None:

        (
            self.db.table(self.TABLE)
            .update(
                {
                    "is_active": False,
                }
            )
            .eq("id", member_id)
            .execute()
        )

    # ---------------------------------------------------------
    # Delete Membership
    # ---------------------------------------------------------

    async def delete(
        self,
        member_id: str,
    ) -> None:

        (
            self.db.table(self.TABLE)
            .delete()
            .eq("id", member_id)
            .execute()
        )

    # ---------------------------------------------------------
    # Exists
    # ---------------------------------------------------------

    async def exists(
        self,
        org_id: str,
        user_id: str,
    ) -> bool:

        result = (
            self.db.table(self.TABLE)
            .select("id")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    # ---------------------------------------------------------
    # Count Members
    # ---------------------------------------------------------

    async def count(
        self,
        org_id: str,
    ) -> int:

        result = (
            self.db.table(self.TABLE)
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", org_id)
            .eq("is_active", True)
            .execute()
        )

        return result.count or 0