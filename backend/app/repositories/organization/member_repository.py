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

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import OrgRole
from app.mappers.organization_mapper import OrganizationMemberMapper
from app.models.domain.organization import OrganizationMember
from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository):
    """
    Repository for org_members.
    """

    table_name = "org_members"
    mapper = OrganizationMemberMapper

    async def create_membership(
        self,
        member: OrganizationMember | dict,
    ) -> OrganizationMember | None:
        return await self.create(member)

    async def get_membership(
        self,
        membership_id: UUID,
    ) -> OrganizationMember | None:
        return await self.get(membership_id)

    async def update_membership(
        self,
        membership_id: UUID,
        data,
    ) -> OrganizationMember | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            membership_id,
            data,
        )

    async def delete_membership(
        self,
        membership_id: UUID,
    ) -> bool:
        return await self.delete(membership_id)

    # --------------------------------------------------------

    async def get_org_member(
        self,
        org_id: UUID,
        user_id: UUID,
    ) -> OrganizationMember | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def get_by_invite_token(
        self,
        token: str,
    ) -> OrganizationMember | None:

        response = (
            self.table()
            .select("*")
            .eq("invite_token", token)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_organization_members(
        self,
        org_id: UUID,
    ) -> list[OrganizationMember]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at")
            .execute()
        )

        return self._many(response)

    async def list_user_memberships(
        self,
        user_id: UUID,
    ) -> list[OrganizationMember]:

        response = (
            self.table()
            .select("*")
            .eq("user_id", str(user_id))
            .execute()
        )

        return self._many(response)

    async def list_role_members(
        self,
        org_id: UUID,
        role: OrgRole,
    ) -> list[OrganizationMember]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("role", role.value)
            .execute()
        )

        return self._many(response)

    async def list_active_members(
        self,
        org_id: UUID,
    ) -> list[OrganizationMember]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_active", True)
            .execute()
        )

        return self._many(response)

    # --------------------------------------------------------

    async def store_invitation(
        self,
        membership_id: UUID,
        invite_email: str,
        invite_token: str,
        expires_at: datetime,
    ) -> OrganizationMember | None:

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
        membership_id: UUID,
    ) -> OrganizationMember | None:

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
        membership_id: UUID,
    ) -> OrganizationMember | None:

        return await self.update_membership(
            membership_id,
            {
                "joined_at": datetime.now(UTC),
                "is_active": True,
                "invite_email": None,
                "invite_token": None,
                "invite_expires_at": None,
            },
        )

    # --------------------------------------------------------

    async def count_active_members(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select("id", count="exact")
            .eq("org_id", str(org_id))
            .eq("is_active", True)
            .execute()
        )

        return response.count or 0

    async def count_members(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select("id", count="exact")
            .eq("org_id", str(org_id))
            .execute()
        )

        return response.count or 0

    async def role_exists(
        self,
        org_id: UUID,
        role: OrgRole,
    ) -> bool:

        response = (
            self.table()
            .select("id")
            .eq("org_id", str(org_id))
            .eq("role", role.value)
            .limit(1)
            .execute()
        )

        return bool(response.data)

    # ========================================================
    # Member State
    # ========================================================

    async def activate_member(
        self,
        membership_id: UUID,
    ) -> OrganizationMember | None:

        return await self.update_membership(
            membership_id,
            {
                "is_active": True,
                "deactivated_at": None,
                "deactivated_by": None,
            },
        )


    async def deactivate_member(
        self,
        membership_id: UUID,
        deactivated_by: UUID,
    ) -> OrganizationMember | None:

        return await self.update_membership(
            membership_id,
            {
                "is_active": False,
                "deactivated_at": datetime.now(UTC),
                "deactivated_by": str(deactivated_by),
            },
        )


    # ========================================================
    # Role
    # ========================================================

    async def change_role(
        self,
        membership_id: UUID,
        role: OrgRole,
    ) -> OrganizationMember | None:

        return await self.update_membership(
            membership_id,
            {
                "role": role.value,
            },
        )


    # ========================================================
    # Profile
    # ========================================================

    async def change_department(
        self,
        membership_id: UUID,
        department: str | None,
    ) -> OrganizationMember | None:

        return await self.update_membership(
            membership_id,
            {
                "department": department,
            },
        )


    async def change_cost_center(
        self,
        membership_id: UUID,
        cost_center: str | None,
    ) -> OrganizationMember | None:

        return await self.update_membership(
            membership_id,
            {
                "cost_center": cost_center,
            },
        )


    async def change_spending_limit(
        self,
        membership_id: UUID,
        spending_limit,
    ) -> OrganizationMember | None:

        return await self.update_membership(
            membership_id,
            {
                "spending_limit": spending_limit,
            },
        )


    # ========================================================
    # Ownership
    # ========================================================

    async def owner_count(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select("id", count="exact")
            .eq("org_id", str(org_id))
            .eq("role", OrgRole.OWNER.value)
            .eq("is_active", True)
            .execute()
        )

        return response.count or 0


    async def get_owner(
        self,
        org_id: UUID,
    ) -> OrganizationMember | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("role", OrgRole.OWNER.value)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        return self._one(response)