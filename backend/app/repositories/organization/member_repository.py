"""
============================================================
Member Repository

Persistence layer for organization memberships.

Owns the org_members table.

Responsibilities
----------------
- Membership CRUD
- Organization member lookups
- Invitation persistence
- Member activation/deactivation

No business logic.
No authorization.
============================================================
"""

from datetime import UTC, datetime
from typing import Any

from backend.app.core.enum.enums import OrgRole
from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository):
    """
    Repository for organization memberships.
    """

    TABLE = "org_members"

    def table(self):
        return self.db.table(self.TABLE)

    # =========================================================
    # Creation
    # =========================================================

    async def create_membership(
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

    async def get_membership(
        self,
        org_id: str,
        user_id: str,
    ) -> dict | None:

        result = (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_by_invite_token(
        self,
        token: str,
    ) -> dict | None:

        result = (
            self.table()
            .select("*")
            .eq("invite_token", token)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_organization_members(
        self,
        org_id: str,
    ) -> list[dict]:

        result = (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .order("created_at")
            .execute()
        )

        return result.data or []

    async def list_user_memberships(
        self,
        user_id: str,
    ) -> list[dict]:

        result = (
            self.table()
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        return result.data or []

    async def list_role_members(
        self,
        org_id: str,
        role: OrgRole,
    ) -> list[dict]:

        result = (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("role", role.value)
            .execute()
        )

        return result.data or []

    async def list_active_members(
        self,
        org_id: str,
    ) -> list[dict]:

        result = (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("is_active", True)
            .execute()
        )

        return result.data or []
    
        # =========================================================
    # Invitations
    # =========================================================

    async def store_invitation(
        self,
        membership_id: str,
        invite_email: str,
        invite_token: str,
        expires_at: datetime,
    ) -> dict:
        """
        Store invitation information for a membership.
        """

        return await self.update_membership(
            membership_id,
            {
                "invite_email": invite_email,
                "invite_token": invite_token,
                "invite_expires_at": expires_at,
            },
        )

    async def clear_invitation(
        self,
        membership_id: str,
    ) -> dict:
        """
        Clear invitation data after acceptance or cancellation.
        """

        return await self.update_membership(
            membership_id,
            {
                "invite_email": None,
                "invite_token": None,
                "invite_expires_at": None,
            },
        )

    async def mark_invitation_accepted(
        self,
        membership_id: str,
    ) -> dict:
        """
        Mark an invitation as accepted.
        """

        return await self.update_membership(
            membership_id,
            {
                "joined_at": datetime.now(UTC),
                "is_active": True,
                "invite_token": None,
                "invite_email": None,
                "invite_expires_at": None,
            },
        )
    
        # =========================================================
    # Helpers
    # =========================================================

    async def membership_exists(
        self,
        org_id: str,
        user_id: str,
    ) -> bool:
        """
        Check whether a user belongs to an organization.
        """

        result = (
            self.table()
            .select("id")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def count_active_members(
        self,
        org_id: str,
    ) -> int:
        """
        Count active organization members.
        """

        result = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", org_id)
            .eq("is_active", True)
            .execute()
        )

        return result.count or 0

    async def count_members(
        self,
        org_id: str,
    ) -> int:
        """
        Count all organization members.
        """

        result = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", org_id)
            .execute()
        )

        return result.count or 0

    async def role_exists(
        self,
        org_id: str,
        role: OrgRole,
    ) -> bool:
        """
        Check whether an organization has at least one member
        with the specified role.
        """

        result = (
            self.table()
            .select("id")
            .eq("org_id", org_id)
            .eq("role", role.value)
            .limit(1)
            .execute()
        )

        return bool(result.data)