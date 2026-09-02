"""
============================================================
Purchase Orders Router

New file — the PurchaseOrderService and PurchaseOrderRepository
underneath this already existed fully built (create, get, update,
delete, match_document, recalculate_matched_amount,
close_if_fully_matched) but had no HTTP entrypoint. This is that
entrypoint, matching the pattern already used by
routers/approvals.py and routers/vendors.py.

See BACKEND_INTEGRATION_AP_DASHBOARD.md §10 for the response
contract the frontend already expects from these routes.
============================================================
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context
from app.core.permissions import MANAGE_VENDORS, VIEW_VENDORS
from app.core.container import get_container
from app.models.domain.purchase_order import PurchaseOrder

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


def _service():
    return get_container().purchase_order_service


class PurchaseOrderCreateRequest(BaseModel):
    po_number: str
    vendor_id: UUID | None = None
    amount: Decimal
    currency: str = "USD"
    description: str | None = None
    issued_date: date | None = None
    expiry_date: date | None = None


class PurchaseOrderUpdateRequest(BaseModel):
    description: str | None = None
    amount: Decimal | None = None
    expiry_date: date | None = None
    is_open: bool | None = None


@router.get("")
async def list_purchase_orders(
    vendor_id: UUID | None = None,
    is_open: bool | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=25, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if VIEW_VENDORS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    return await _service().list_purchase_orders(
        org_id=ctx.org_id,
        vendor_id=vendor_id,
        is_open=is_open,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/{purchase_order_id}")
async def get_purchase_order(
    purchase_order_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if VIEW_VENDORS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    po = await _service().get(purchase_order_id)
    if po is None or po.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.post("")
async def create_purchase_order(
    payload: PurchaseOrderCreateRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if MANAGE_VENDORS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    return await _service().create(
        PurchaseOrder(
            id=uuid4(),
            org_id=ctx.org_id,
            created_by=user.id,
            **payload.model_dump(),
        )
    )


@router.patch("/{purchase_order_id}")
async def update_purchase_order(
    purchase_order_id: UUID,
    payload: PurchaseOrderUpdateRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if MANAGE_VENDORS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing = await _service().get(purchase_order_id)
    if existing is None or existing.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return await _service().update(purchase_order_id, updates)
