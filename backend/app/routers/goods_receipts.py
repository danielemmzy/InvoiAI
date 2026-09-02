from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.context import OrganizationContext
from app.core.ocm import get_org_context
from app.core.permissions import VIEW_FINANCE, MANAGE_FINANCE
from app.core.authorization import require_permission
from app.core.supabase import get_supabase

router = APIRouter(prefix="/goods-receipts", tags=["Goods Receipts"])


@router.get("/po/{purchase_order_id}")
async def list_receipts(
    purchase_order_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    return (
        get_supabase()
        .table("goods_receipts")
        .select("*, goods_receipt_lines(*)")
        .eq("org_id", str(ctx.org_id))
        .eq("purchase_order_id", str(purchase_order_id))
        .order("received_at", desc=True)
        .execute()
        .data
        or []
    )


@router.post("")
async def create_receipt(
    body: dict,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    db = get_supabase()
    lines = body.pop("lines", [])
    body["org_id"] = str(ctx.org_id)
    body["received_by"] = str(ctx.user_id)
    receipt = db.table("goods_receipts").insert(body).execute().data[0]
    if lines:
        db.table("goods_receipt_lines").insert(
            [{**line, "goods_receipt_id": receipt["id"]} for line in lines]
        ).execute()
    return (
        db.table("goods_receipts")
        .select("*, goods_receipt_lines(*)")
        .eq("id", receipt["id"])
        .single()
        .execute()
        .data
    )
