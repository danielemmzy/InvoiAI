"""
============================================================
Members Router

Flow 11 — POST /members/invite, POST /members/accept-invite,
GET /members.

MemberService already existed fully built but had no HTTP
entrypoint. Its invite_member(membership_id, email) expects an
existing pending membership row, so the invite flow here is:
create_membership() (role/department/spending_limit, inactive)
-> invite_member() (generates + stores the token) — matching
Flow 11's two-part "org_members table INSERT" + "invite_token"
description in one request.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.enum.database import OrgRole
from app.core.ocm import get_org_context
from app.core.permissions import INVITE_MEMBERS, REMOVE_MEMBERS, VIEW_MEMBERS, MANAGE_AP_RULES, MANAGE_ROLES, MANAGE_APPROVAL_AUTHORITY
from app.services.member_service import MemberService
from app.core.container import get_container

router = APIRouter(prefix="/members", tags=["Members"])


class InviteMemberRequest(BaseModel):
    email: str
    role: OrgRole = OrgRole.MEMBER
    department: str | None = None
    spending_limit: float | None = None


class AcceptInviteRequest(BaseModel):
    token: str


class MemberApprovalLimitsRequest(BaseModel):
    spending_limit: float | None = None
    payment_approval_limit: float | None = None
    supervisor_id: UUID | None = None


@router.get("")
async def list_members(
    ctx: OrganizationContext = Depends(get_org_context),
):
    if VIEW_MEMBERS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")
    members = await get_container().member_service.list_members(ctx.org_id)
    return [m.model_dump(mode="json") for m in members]


@router.post("/invite", status_code=201)
async def invite_member(
    payload: InviteMemberRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if INVITE_MEMBERS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = get_container().member_service

    membership = await service.members.create_membership(
        {
            "org_id": ctx.org_id,
            "role": payload.role.value,
            "department": payload.department,
            "spending_limit": payload.spending_limit,
            "invited_by": user.id,
            "is_active": False,
        }
    )
    # NOTE: Flow 11 specifies checking member_repository.get_by_invite_email
    # for a 409 duplicate-invite conflict before creating the row, but
    # no such repository method exists in this codebase (only
    # get_by_invite_token, which needs a token that doesn't exist
    # yet at this point). Skipped rather than calling a method that
    # isn't there — add get_by_invite_email to MemberRepository if
    # you want that guard back.

    invitation = await service.invite_member(membership.id, payload.email)

    if payload.spending_limit is not None:
        try:
            organization = await get_container().organization_service.organizations.get_organization(ctx.org_id)
            currency = (organization.currency if organization else "USD").upper()
            await get_container().approval_authority_service.authorities.upsert(
                ctx.org_id, membership.id, {
                    "approval_type": "invoice", "currency": currency,
                    "limit_amount": str(payload.spending_limit),
                    "can_self_approve": False, "can_approve_exceptions": True,
                }
            )
        except Exception:
            pass

    return {
        "membership_id": str(membership.id),
        "invite_email": payload.email,
        "status": "invited",
        "invite_expires_at": (
            invitation.invite_expires_at.isoformat()
            if getattr(invitation, "invite_expires_at", None)
            else None
        ),
    }


@router.post("/accept-invite")
async def accept_invite(
    payload: AcceptInviteRequest,
    user: AuthUser = Depends(get_current_user),
):
    """
    Flow 11: "member_repository.get_by_invite_token(token) ->
    NOT FOUND -> 404, EXPIRED -> 400 -> org_members UPDATE:
    user_id, is_active: true, joined_at: now(), invite_token: null".
    MemberService.accept_invitation already implements exactly
    this (404/400 raised internally) — this just exposes it.
    """
    service = get_container().member_service
    membership = await service.accept_invitation(payload.token)

    await service.members.update_membership(
        membership.id,
        {"user_id": user.id},
    )

    return {"membership_id": str(membership.id), "status": "active"}



class MemberRoleRequest(BaseModel):
    role: OrgRole


@router.patch("/{membership_id}/role")
async def change_member_role(
    membership_id: UUID,
    payload: MemberRoleRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if MANAGE_ROLES not in ctx.permissions and "*" not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")
    service = get_container().member_service
    member = await service.ensure_member_exists(membership_id)
    if member.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Member not found")
    actor = await service.members.get_org_member(ctx.org_id, user.id)
    if actor is None:
        raise HTTPException(status_code=403, detail="Not authorized")
    if payload.role == OrgRole.OWNER and actor.role != OrgRole.OWNER:
        raise HTTPException(status_code=403, detail="Only an organization owner can assign the owner role.")
    if member.role == OrgRole.OWNER and actor.role != OrgRole.OWNER:
        raise HTTPException(status_code=403, detail="Only an organization owner can modify another owner.")
    if member.role == OrgRole.OWNER and payload.role != OrgRole.OWNER:
        await service.ensure_not_last_owner(ctx.org_id)
    updated = await service.members.change_role(membership_id, payload.role)
    return updated.model_dump(mode="json")

@router.patch("/{membership_id}/access-role/{role_id}")
async def change_member_access_role(
    membership_id: UUID,
    role_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if MANAGE_ROLES not in ctx.permissions and "*" not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")
    service = get_container().member_service
    member = await service.ensure_member_exists(membership_id)
    actor = await service.members.get_org_member(ctx.org_id, user.id)
    if actor is None or member.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Member not found")
    profile = get_container().db.table("organization_roles").select("id,role_key,name,permissions,is_system").eq("org_id", str(ctx.org_id)).eq("id", str(role_id)).limit(1).execute().data or []
    if not profile:
        raise HTTPException(status_code=404, detail="Access role not found")
    role = profile[0]
    if role.get("role_key") == "owner" and actor.role != OrgRole.OWNER:
        raise HTTPException(status_code=403, detail="Only an organization owner can assign the owner access profile.")
    if member.role == OrgRole.OWNER and actor.role != OrgRole.OWNER:
        raise HTTPException(status_code=403, detail="Only an organization owner can modify another owner.")
    if member.role == OrgRole.OWNER and role.get("role_key") != "owner":
        await service.ensure_not_last_owner(ctx.org_id)

    compatible = {r.value for r in OrgRole}
    updates = {"access_role_id": str(role_id)}
    if role.get("role_key") in compatible:
        updates["role"] = role["role_key"]
    updated = await service.members.update_membership(membership_id, updates)
    return updated.model_dump(mode="json") if updated else None

@router.delete("/{membership_id}")
async def remove_member(
    membership_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if REMOVE_MEMBERS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    await get_container().member_service.remove_member(user, membership_id)
    return {"status": "removed"}


@router.patch("/{membership_id}/approval-limits")
async def set_approval_limits(
    membership_id: UUID,
    payload: MemberApprovalLimitsRequest,
    ctx: OrganizationContext = Depends(get_org_context),
):
    """
    Sets a member's bill approval limit, payment approval limit,
    and supervisor (org_members.id of who they escalate to when a
    document exceeds their limit). Consumed by APRoutingEngine's
    auto-escalation chain.
    """
    if MANAGE_AP_RULES not in ctx.permissions and MANAGE_APPROVAL_AUTHORITY not in ctx.permissions and "*" not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    repo = get_container().member_repository
    existing = await repo.get_membership(membership_id)
    if existing is None or str(existing.org_id) != str(ctx.org_id):
        raise HTTPException(status_code=404, detail="Member not found.")

    if payload.supervisor_id is not None and str(payload.supervisor_id) == str(membership_id):
        raise HTTPException(status_code=422, detail="A member cannot be their own supervisor.")

    if payload.supervisor_id is not None:
        supervisor = await repo.get_membership(payload.supervisor_id)
        if supervisor is None or str(supervisor.org_id) != str(ctx.org_id):
            raise HTTPException(status_code=422, detail="supervisor_id must belong to a member of the same organization.")
        if not supervisor.is_active:
            raise HTTPException(status_code=422, detail="supervisor_id must be an active member.")

        # Walk the proposed supervisor's own chain to reject a cycle
        # (A supervises B, B supervises C, C supervises A) before it's
        # ever written — APRoutingEngine's escalation walk also caps
        # depth and dedupes as a second line of defense at read time,
        # but rejecting the cycle at write time is the correct place
        # to stop it.
        seen = {str(membership_id)}
        cursor = supervisor
        for _ in range(10):
            if str(cursor.id) in seen:
                raise HTTPException(status_code=422, detail="This assignment would create a supervisor cycle.")
            seen.add(str(cursor.id))
            if cursor.supervisor_id is None:
                break
            cursor = await repo.get_membership(cursor.supervisor_id)
            if cursor is None:
                break

    updates = payload.model_dump(exclude_unset=True)
    updated = await repo.update_membership(membership_id, updates)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to update member.")

    # Keep the legacy member limits and the normalized approval-authority
    # records in sync. Existing routing continues to work while the new
    # approval engine enforces authority at decision time.
    try:
        org = get_container().organization_service
        organization = await org.organizations.get_organization(ctx.org_id)
        currency = (organization.currency if organization else "USD").upper()
        if "spending_limit" in updates and payload.spending_limit is None:
            await get_container().approval_authority_service.authorities.deactivate(
                ctx.org_id, membership_id, "invoice"
            )
        elif payload.spending_limit is not None:
            await get_container().approval_authority_service.authorities.upsert(
                ctx.org_id, membership_id, {
                    "approval_type": "invoice", "currency": currency,
                    "limit_amount": str(payload.spending_limit),
                    "can_self_approve": False, "can_approve_exceptions": True,
                }
            )
        if "payment_approval_limit" in updates and payload.payment_approval_limit is None:
            await get_container().approval_authority_service.authorities.deactivate(
                ctx.org_id, membership_id, "payment"
            )
        elif payload.payment_approval_limit is not None:
            await get_container().approval_authority_service.authorities.upsert(
                ctx.org_id, membership_id, {
                    "approval_type": "payment", "currency": currency,
                    "limit_amount": str(payload.payment_approval_limit),
                    "can_self_approve": False, "can_approve_exceptions": False,
                }
            )
    except Exception:
        # The normalized tables are introduced by the additive migration;
        # legacy limit persistence remains authoritative until it is applied.
        pass

    return updated.model_dump(mode="json")
