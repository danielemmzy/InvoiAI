from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context
from app.core.container import get_container
from app.core.cache import cache
from app.core.cache_keys import vendors as vendors_cache_key
from app.core.limiter import limiter
from app.core.authorization import require_permission
from app.core.permissions import VIEW_VENDORS, MANAGE_VENDORS
from app.schemas.vendor import VendorResponse, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["Vendors"])


def _responses(vendors):
    return [VendorResponse.model_validate(v, from_attributes=True) for v in vendors]


@router.get("/preferred/list", response_model=list[VendorResponse])
async def preferred_vendors(
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_VENDORS)),
):
    return _responses(await get_container().vendor_service.list_preferred(ctx.org_id))


@router.get("/blocked/list", response_model=list[VendorResponse])
async def blocked_vendors(
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_VENDORS)),
):
    return _responses(await get_container().vendor_service.list_blocked(ctx.org_id))


@router.get("", response_model=list[VendorResponse])
@limiter.limit("60/minute")
async def list_vendors(
    response: Response,
    request: Request,
    query: str | None = None,
    limit: int = 50,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_VENDORS)),
):
    limit = min(max(limit, 1), 100)
    key = vendors_cache_key(str(ctx.org_id), query, limit)
    cached = await cache.get(key)
    if cached is not None:
        return [VendorResponse.model_validate(item) for item in cached]

    service = get_container().vendor_service
    vendors = (
        await service.search_vendors(ctx.org_id, query, limit)
        if query
        else await service.list_for_org(ctx.org_id, limit=limit)
    )
    result = _responses(vendors)
    await cache.set(
        key=key,
        value=[item.model_dump(mode="json") for item in result],
        ttl=120,
    )
    return result


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_VENDORS)),
):
    vendor = await get_container().vendor_service.get_vendor(vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return VendorResponse.model_validate(vendor, from_attributes=True)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: UUID,
    payload: VendorUpdate,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_VENDORS)),
):
    service = get_container().vendor_service
    vendor = await service.get_vendor(vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    try:
        updated = await service.update_vendor(vendor_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await cache.delete_prefix(f"v2:vendors:{ctx.org_id}:")
    return VendorResponse.model_validate(updated, from_attributes=True)


@router.delete("/{vendor_id}", status_code=204)
async def delete_vendor(
    vendor_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_VENDORS)),
):
    service = get_container().vendor_service
    vendor = await service.get_vendor(vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await service.delete_vendor(vendor_id)
    await cache.delete_prefix(f"v2:vendors:{ctx.org_id}:")


@router.post("/{vendor_id}/preferred", response_model=VendorResponse)
async def mark_preferred(
    vendor_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_VENDORS)),
):
    service = get_container().vendor_service
    vendor = await service.get_vendor(vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    result = await service.mark_preferred(vendor_id)
    await cache.delete_prefix(f"v2:vendors:{ctx.org_id}:")
    return VendorResponse.model_validate(result, from_attributes=True)


@router.delete("/{vendor_id}/preferred", response_model=VendorResponse)
async def remove_preferred(
    vendor_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_VENDORS)),
):
    service = get_container().vendor_service
    vendor = await service.get_vendor(vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    result = await service.remove_preferred(vendor_id)
    await cache.delete_prefix(f"v2:vendors:{ctx.org_id}:")
    return VendorResponse.model_validate(result, from_attributes=True)


@router.post("/{vendor_id}/block", response_model=VendorResponse)
async def block_vendor(
    vendor_id: UUID,
    reason: str,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_VENDORS)),
):
    service = get_container().vendor_service
    vendor = await service.get_vendor(vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    result = await service.block_vendor(vendor_id, reason)
    await cache.delete_prefix(f"v2:vendors:{ctx.org_id}:")
    return VendorResponse.model_validate(result, from_attributes=True)


@router.delete("/{vendor_id}/block", response_model=VendorResponse)
async def unblock_vendor(
    vendor_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_VENDORS)),
):
    service = get_container().vendor_service
    vendor = await service.get_vendor(vendor_id)
    if vendor is None or vendor.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    result = await service.unblock_vendor(vendor_id)
    await cache.delete_prefix(f"v2:vendors:{ctx.org_id}:")
    return VendorResponse.model_validate(result, from_attributes=True)
