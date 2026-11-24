from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.context import OrganizationContext
from app.core.ocm import get_org_context
from app.core.permissions import MANAGE_APPROVAL_AUTHORITY, MANAGE_DELEGATIONS, MANAGE_ROLES, MANAGE_SOD
from app.core.supabase import get_supabase
from app.core.container import get_container

router = APIRouter(prefix="/organization-access", tags=["Organization Access & Approval Authority"])

from app.core.db import execute

class AuthorityRequest(BaseModel):
    membership_id: UUID
    approval_type: str = Field(pattern="^(invoice|payment)$")
    currency: str = Field(min_length=3, max_length=3)
    limit_amount: Decimal = Field(ge=0)
    can_self_approve: bool = False
    can_approve_exceptions: bool = False
    effective_from: datetime | None = None
    effective_until: datetime | None = None

class DelegationRequest(BaseModel):
    delegator_membership_id: UUID
    delegatee_membership_id: UUID
    scope: dict[str, bool] = {"invoice": True, "payment": False}
    starts_at: datetime
    ends_at: datetime
    reason: str | None = None

class RoleRequest(BaseModel):
    role_key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


def _require(ctx: OrganizationContext, permission: str):
    if permission not in ctx.permissions and "*" not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

@router.get("/authorities")
async def list_authorities(ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_APPROVAL_AUTHORITY)
    return (await execute(get_supabase().table("approval_authorities").select("*").eq("org_id", str(ctx.org_id)).eq("is_active", True).order("limit_amount"))).data or []

@router.put("/authorities")
async def upsert_authority(payload: AuthorityRequest, ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_APPROVAL_AUTHORITY)
    member = (await execute(get_supabase().table("org_members").select("id").eq("org_id", str(ctx.org_id)).eq("id", str(payload.membership_id)).limit(1))).data or []
    if not member: raise HTTPException(status_code=404, detail="Membership not found")
    data = payload.model_dump(mode="json")
    data["currency"] = data["currency"].upper()
    data["limit_amount"] = str(payload.limit_amount)
    return await get_container().approval_authority_service.authorities.upsert(ctx.org_id, payload.membership_id, data)

@router.get("/delegations")
async def list_delegations(ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_DELEGATIONS)
    return await get_container().approval_authority_service.delegations.list_active(ctx.org_id)

@router.post("/delegations", status_code=201)
async def create_delegation(payload: DelegationRequest, ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_DELEGATIONS)
    if payload.starts_at >= payload.ends_at: raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    db = get_supabase()
    members = (await execute(db.table("org_members").select("id").eq("org_id", str(ctx.org_id)).in_("id", [str(payload.delegator_membership_id), str(payload.delegatee_membership_id)]))).data or []
    if len(members) != 2: raise HTTPException(status_code=404, detail="Both memberships must belong to this organization")
    if payload.delegator_membership_id == payload.delegatee_membership_id: raise HTTPException(status_code=400, detail="A member cannot delegate to themselves")
    result = await get_container().approval_authority_service.delegations.create(ctx.org_id, {**payload.model_dump(mode="json"), "created_by": str(UUID(ctx.user_id))})
    try:
        await get_container().audit_service.log(org_id=ctx.org_id, user_id=UUID(ctx.user_id), action="approval.delegation_created", resource_type="approval_delegation", resource_id=UUID(result["id"]), old_values={}, new_values=result)
    except Exception:
        pass
    return result

@router.post("/delegations/{delegation_id}/revoke")
async def revoke_delegation(delegation_id: UUID, ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_DELEGATIONS)
    result = await get_container().approval_authority_service.delegations.revoke(ctx.org_id, delegation_id)
    try:
        await get_container().audit_service.log(org_id=ctx.org_id, user_id=UUID(ctx.user_id), action="approval.delegation_revoked", resource_type="approval_delegation", resource_id=delegation_id, old_values={}, new_values=result)
    except Exception:
        pass
    return result

@router.get("/roles")
async def list_roles(ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_ROLES)
    return (await execute(get_supabase().table("organization_roles").select("*").eq("org_id", str(ctx.org_id)).eq("is_active", True).order("is_system", desc=True).order("name"))).data or []

@router.post("/roles", status_code=201)
async def create_role(payload: RoleRequest, ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_ROLES)
    db = get_supabase()
    existing = (await execute(db.table("organization_roles").select("id").eq("org_id", str(ctx.org_id)).eq("role_key", payload.role_key).limit(1))).data or []
    if existing: raise HTTPException(status_code=409, detail="Role key already exists")
    return (await execute(db.table("organization_roles").insert({**payload.model_dump(), "org_id": str(ctx.org_id), "is_system": False}))).data[0]

@router.get("/sod-rules")
async def list_sod_rules(ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, MANAGE_SOD)
    return (await execute(get_supabase().table("sod_rules").select("*").eq("org_id", str(ctx.org_id)).order("rule_key"))).data or []
