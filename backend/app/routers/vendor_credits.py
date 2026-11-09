from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.authorization import require_permission
from app.core.ocm import get_org_context
from app.core.permissions import VIEW_VENDORS, MANAGE_VENDORS
from app.services.vendor.vendor_credit_service import VendorCreditService

router=APIRouter(prefix="/vendors",tags=["Vendor credits"])
class CreditCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD",min_length=3,max_length=3)
    credit_number: str | None = Field(default=None,max_length=100)
    reason: str | None = Field(default=None,max_length=300)
    issued_at: str | None = None
    expires_at: str | None = None
    notes: str | None = Field(default=None,max_length=4000)
class CreditApply(BaseModel):
    document_id: UUID
    amount: Decimal = Field(gt=0)
class CreditCancel(BaseModel):
    reason: str = Field(min_length=3,max_length=500)

def _run(awaitable): return awaitable

@router.get("/{vendor_id}/credits")
async def list_vendor_credits(vendor_id: UUID,ctx:OrganizationContext=Depends(get_org_context),_:None=Depends(require_permission(VIEW_VENDORS))):
    try:return await VendorCreditService().list_for_vendor(ctx.org_id,vendor_id)
    except ValueError as e:raise HTTPException(404,detail=str(e)) from e

@router.post("/{vendor_id}/credits",status_code=201)
async def create_vendor_credit(vendor_id:UUID,payload:CreditCreate,user:AuthUser=Depends(get_current_user),ctx:OrganizationContext=Depends(get_org_context),_:None=Depends(require_permission(MANAGE_VENDORS))):
    try:return await VendorCreditService().create(ctx.org_id,vendor_id,user.id,payload.model_dump())
    except ValueError as e:raise HTTPException(422,detail=str(e)) from e

@router.post("/credits/{credit_id}/apply",status_code=201)
async def apply_vendor_credit(credit_id:UUID,payload:CreditApply,user:AuthUser=Depends(get_current_user),ctx:OrganizationContext=Depends(get_org_context),_:None=Depends(require_permission(MANAGE_VENDORS))):
    try:return await VendorCreditService().apply(ctx.org_id,credit_id,user.id,payload.document_id,payload.amount)
    except ValueError as e:raise HTTPException(422,detail=str(e)) from e

@router.post("/credits/{credit_id}/cancel")
async def cancel_vendor_credit(credit_id:UUID,payload:CreditCancel,user:AuthUser=Depends(get_current_user),ctx:OrganizationContext=Depends(get_org_context),_:None=Depends(require_permission(MANAGE_VENDORS))):
    try:return await VendorCreditService().cancel(ctx.org_id,credit_id,user.id,payload.reason)
    except ValueError as e:raise HTTPException(422,detail=str(e)) from e

@router.get("/credits/{credit_id}/events")
async def vendor_credit_events(credit_id:UUID,ctx:OrganizationContext=Depends(get_org_context),_:None=Depends(require_permission(VIEW_VENDORS))):
    try:return await VendorCreditService().events(ctx.org_id,credit_id)
    except ValueError as e:raise HTTPException(404,detail=str(e)) from e
