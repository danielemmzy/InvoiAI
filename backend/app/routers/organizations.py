from __future__ import annotations

from fastapi import APIRouter, Depends
from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context
from app.core.container import get_container
from app.core.cache import cache
from app.core.cache_keys import organization as organization_cache_key, organization_permissions

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("/current")
async def current_organization(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    key = organization_cache_key(str(ctx.org_id))
    cached = await cache.get(key)
    if cached is not None:
        return cached
    result = ctx.model_dump(mode="json")
    await cache.set(key=key, value=result, ttl=60)
    return result

@router.get("/permissions")
async def organization_permissions(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    key = organization_permissions(str(ctx.org_id), str(user.id))
    cached = await cache.get(key)
    if cached is not None:
        return cached
    permissions = await get_container().organization_service.get_permissions(
        org_id=ctx.org_id, user_id=user.id
    )
    result = {"permissions": sorted(permissions)}
    await cache.set(key=key, value=result, ttl=60)
    return result
