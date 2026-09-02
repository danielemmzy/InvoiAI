from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets
from uuid import UUID

from fastapi import HTTPException, status

from app.context.auth import AuthUser
from app.core.enum.database import OrgRole
from app.core.permissions import get_permissions

from app.repositories.audit.audit_repository import AuditRepository
from app.repositories.organization.member_repository import MemberRepository
from app.repositories.organization.organization_repository import (
    OrganizationRepository,
)
from app.repositories.organization.organization_settings_repository import (
    OrganizationSettingsRepository,
)


class MemberService:
    """
    Business logic for organization members.

    Owns:

    - invitations
    - activation
    - deactivation
    - ownership
    - role management
    """

    def __init__(self) -> None:
        self.members = MemberRepository()
        self.organizations = OrganizationRepository()
        self.settings = OrganizationSettingsRepository()
        self.audit = AuditRepository()

    # =====================================================
    # Retrieval
    # =====================================================

    async def get_member(
        self,
        membership_id: UUID,
    ):
        return await self.members.get_membership(membership_id)

    async def list_members(
        self,
        org_id: UUID,
    ):
        return await self.members.list_organization_members(org_id)

    async def list_active_members(
        self,
        org_id: UUID,
    ):
        return await self.members.list_active_members(org_id)

    async def list_role_members(
        self,
        org_id: UUID,
        role: OrgRole,
    ):
        return await self.members.list_role_members(
            org_id,
            role,
        )

    async def list_my_memberships(
        self,
        user_id: UUID,
    ):
        return await self.members.list_user_memberships(user_id)

    # =====================================================
    # Invitations
    # =====================================================

    async def invite_member(
        self,
        membership_id: UUID,
        email: str,
    ):
        token = secrets.token_urlsafe(48)

        expires = datetime.now(UTC) + timedelta(days=7)

        return await self.members.store_invitation(
            membership_id=membership_id,
            invite_email=email,
            invite_token=token,
            expires_at=expires,
        )

    async def resend_invitation(
        self,
        membership_id: UUID,
        email: str,
    ):
        return await self.invite_member(
            membership_id,
            email,
        )

    async def cancel_invitation(
        self,
        membership_id: UUID,
    ):
        return await self.members.clear_invitation(
            membership_id,
        )

    async def accept_invitation(
        self,
        token: str,
    ):
        invitation = await self.members.get_by_invite_token(
            token,
        )

        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found.",
            )

        if (
            invitation.invite_expires_at
            and invitation.invite_expires_at < datetime.now(UTC)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation expired.",
            )

        return await self.members.mark_invitation_accepted(
            invitation.id,
        )

        # =====================================================
    # Member Management
    # =====================================================

    async def change_role(
        self,
        actor: AuthUser,
        membership_id: UUID,
        role: OrgRole,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        await self.ensure_can_manage_member(
            actor,
            member.org_id,
        )

        if (
            member.role == OrgRole.OWNER
            and role != OrgRole.OWNER
        ):
            await self.ensure_not_last_owner(
                member.org_id,
            )

        return await self.members.change_role(
            membership_id,
            role,
        )

    async def change_department(
        self,
        actor: AuthUser,
        membership_id: UUID,
        department: str | None,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        await self.ensure_can_manage_member(
            actor,
            member.org_id,
        )

        return await self.members.change_department(
            membership_id,
            department,
        )

    async def change_cost_center(
        self,
        actor: AuthUser,
        membership_id: UUID,
        cost_center: str | None,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        await self.ensure_can_manage_member(
            actor,
            member.org_id,
        )

        return await self.members.change_cost_center(
            membership_id,
            cost_center,
        )

    async def change_spending_limit(
        self,
        actor: AuthUser,
        membership_id: UUID,
        spending_limit,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        await self.ensure_can_manage_member(
            actor,
            member.org_id,
        )

        return await self.members.change_spending_limit(
            membership_id,
            spending_limit,
        )

    async def deactivate_member(
        self,
        actor: AuthUser,
        membership_id: UUID,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        await self.ensure_can_manage_member(
            actor,
            member.org_id,
        )

        if member.role == OrgRole.OWNER:
            await self.ensure_not_last_owner(
                member.org_id,
            )

        return await self.members.deactivate_member(
            membership_id,
            actor.id,
        )

    async def activate_member(
        self,
        actor: AuthUser,
        membership_id: UUID,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        await self.ensure_can_manage_member(
            actor,
            member.org_id,
        )

        return await self.members.activate_member(
            membership_id,
        )

    async def remove_member(
        self,
        actor: AuthUser,
        membership_id: UUID,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        await self.ensure_can_manage_member(
            actor,
            member.org_id,
        )

        if member.role == OrgRole.OWNER:
            await self.ensure_not_last_owner(
                member.org_id,
            )

        return await self.members.delete_membership(
            membership_id,
        )

        # =====================================================
    # Ownership
    # =====================================================

    async def transfer_ownership(
        self,
        actor: AuthUser,
        current_owner_membership_id: UUID,
        new_owner_membership_id: UUID,
    ):
        current_owner = await self.ensure_member_exists(
            current_owner_membership_id,
        )

        new_owner = await self.ensure_member_exists(
            new_owner_membership_id,
        )

        if current_owner.org_id != new_owner.org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Members belong to different organizations.",
            )

        await self.ensure_is_owner(actor)

        await self.members.change_role(
            current_owner.id,
            OrgRole.ADMIN,
        )

        await self.members.change_role(
            new_owner.id,
            OrgRole.OWNER,
        )

        return await self.members.get_membership(
            new_owner.id,
        )

    # =====================================================
    # Validation
    # =====================================================

    async def ensure_member_exists(
        self,
        membership_id: UUID,
    ):
        member = await self.members.get_membership(
            membership_id,
        )

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found.",
            )

        return member

    async def ensure_is_owner(
        self,
        actor: AuthUser,
    ):
        if actor.role != OrgRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Owner permission required.",
            )

    async def ensure_not_last_owner(
        self,
        org_id: UUID,
    ):
        owners = await self.members.owner_count(
            org_id,
        )

        if owners <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last organization owner.",
            )

    async def ensure_can_manage_member(
        self,
        actor: AuthUser,
        org_id: UUID,
    ):
        membership = await self.members.get_org_member(
            org_id,
            actor.id,
        )

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization.",
            )

        if membership.role not in (
            OrgRole.OWNER,
            OrgRole.ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

    async def ensure_email_not_invited(
        self,
        membership_id: UUID,
    ):
        member = await self.ensure_member_exists(
            membership_id,
        )

        if member.invite_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Member already has an active invitation.",
            )

    async def ensure_user_not_already_member(
        self,
        org_id: UUID,
        user_id: UUID,
    ):
        member = await self.members.get_org_member(
            org_id,
            user_id,
        )

        if member is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization.",
            )

        # =====================================================
    # Context
    # =====================================================

    async def build_auth_context(
        self,
        user: AuthUser,
    ) -> AuthUser:
        """
        Builds the authenticated request context.

        Supabase Auth remains the source of truth.
        This method enriches the current user with
        organization permissions.
        """

        if user.org_id is None or user.role is None:
            return user

        membership = await self.members.get_org_member(
            user.org_id,
            user.id,
        )

        if membership is None:
            return user.model_copy(
                update={
                    "permissions": set(),
                }
            )

        permissions = self.get_member_permissions(
            membership.role,
        )

        return user.model_copy(
            update={
                "permissions": permissions,
            }
        )

    def get_member_permissions(
        self,
        role: OrgRole,
    ) -> set[str]:
        """
        Returns RBAC permissions for a member.
        """

        return get_permissions(
            role.value,
        )

    # =====================================================
    # Statistics
    # =====================================================

    async def member_count(
        self,
        org_id: UUID,
    ) -> int:
        return await self.members.count_members(
            org_id,
        )

    async def active_member_count(
        self,
        org_id: UUID,
    ) -> int:
        return await self.members.count_active_members(
            org_id,
        )

    async def owner(
        self,
        org_id: UUID,
    ):
        return await self.members.get_owner(
            org_id,
        )