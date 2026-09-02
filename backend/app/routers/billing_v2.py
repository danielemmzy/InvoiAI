from __future__ import annotations
from fastapi import APIRouter, Depends, Request, HTTPException, Response
from pydantic import BaseModel
from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context
from app.core.container import get_container
from app.core.limiter import limiter
from app.core.authorization import require_permission
from app.core.permissions import VIEW_BILLING, MANAGE_BILLING
from app.core.plan import PLANS

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans")
async def list_plans():
    """
    Public plan catalog — powers the pricing page and the in-app
    upgrade screen from one source instead of hardcoding numbers in
    the frontend. See core/plan.py for the definitions themselves.
    """
    return [
        {
            "id": plan.name.value,
            "display_name": plan.display_name,
            "price_monthly": plan.price_monthly,
            "price_annual_monthly": plan.price_annual_monthly,
            "contact_sales": plan.contact_sales,
            "seats": "Unlimited" if plan.unlimited_seats else plan.seats,
            "monthly_documents": "Unlimited" if plan.unlimited_documents else plan.monthly_documents,
            "max_accounting_integrations": plan.max_accounting_integrations,
            "max_matching_ways": plan.max_matching_ways,
            "max_business_workspaces": "Unlimited" if plan.unlimited_business_workspaces else plan.max_business_workspaces,
            "max_batch_upload": plan.max_batch_upload,
            "export_formats": list(plan.export_formats),
            "features": sorted(f.value for f in plan.features),
        }
        for plan in PLANS.values()
    ]


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str
    annual: bool = False


@router.post("/checkout")
@limiter.limit("10/minute")
async def checkout(
    response: Response,
    request: Request,
    body: CheckoutRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if body.plan not in ("starter", "pro", "business"):
        raise HTTPException(400, "Invalid plan")
    try:
        return await get_container().stripe_billing_service.checkout(
            user=user,
            org_id=ctx.org_id,
            plan=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            annual=body.annual,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/subscription")
@limiter.limit("30/minute")
async def subscription(
    response: Response,
    request: Request,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_BILLING)),
):
    sub = await get_container().stripe_billing_service.subscription(ctx.org_id)
    return {
        "plan": ctx.plan,
        "subscription": sub.model_dump(mode="json") if sub else None,
        "usage": {
            "used": ctx.documents_used,
            "remaining": ctx.remaining_documents,
            "limit": ctx.document_limit,
            "limit_reached": ctx.remaining_documents <= 0,
        },
    }


@router.post("/cancel")
@limiter.limit("5/minute")
async def cancel(
    response: Response,
    request: Request,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_BILLING)),
):
    try:
        await get_container().stripe_billing_service.cancel(ctx.org_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"message": "Subscription will cancel at end of current billing period."}
