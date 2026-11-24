"""
============================================================
AP Workflow Engine Router

Endpoints for the pieces added on top of the existing AP
automation pipeline (documents/ap.py, approvals.py):

- /ap/rules            AP routing/approval rules (conditional,
                        amount/vendor/department/location-based)
- /ap/groups           Approval groups (pooled approvers) +
                        membership + claiming a pooled step
- /ap/payments/queue    Bills that cleared approval and are
                        waiting on payment release, each with
                        its authorization status
- /ap/payments/*       Re-evaluate / override payment blocks
- /ap/comments         Tag a teammate on a bill (+ notification)
============================================================
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_verified_user
from pydantic import BaseModel, Field

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.authorization import require_permission
from app.core.enum.ap import (
    ApprovalExecutionMode, ApprovalRuleScope, ApproverType,
    PaymentInstructionStatus, VendorDocumentRequestType,
)
from app.core.ocm import get_org_context
from app.core.permissions import (
    AUTHORIZE_PAYMENTS,
    MANAGE_AP_RULES,
    OVERRIDE_PAYMENT_BLOCKS,
    VIEW_APPROVALS,
    VIEW_FINANCE,
)
from app.services.ap.approval_group_service import ApprovalGroupService
from app.services.ap.approval_rule_service import ApprovalRuleService
from app.services.ap.comment_service import InvoiceCommentService
from app.services.payment.payment_authorization_service import PaymentAuthorizationService
from app.services.payment.payment_instruction_service import PaymentInstructionService

router = APIRouter(
    prefix="/ap",
    tags=["AP Workflow Engine"],
    dependencies=[Depends(require_verified_user)],
)


# ============================================================
# Schemas
# ============================================================

from app.core.db import execute

class ApprovalRuleCreate(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    priority: int = 100
    scope: ApprovalRuleScope = ApprovalRuleScope.BILL
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    vendor_id: UUID | None = None
    department: str | None = None
    cost_center: str | None = None
    location: str | None = None
    document_type: str | None = None
    risk_level: str | None = None
    requires_po: bool | None = None
    step_number: int = 1
    step_name: str = "Approval"
    execution_mode: ApprovalExecutionMode = ApprovalExecutionMode.SEQUENTIAL
    approver_type: ApproverType = ApproverType.ROLE
    approver_id: UUID | None = None
    approver_role: str | None = None
    approver_group_id: UUID | None = None
    conditions: dict | None = None
    actions: list[dict] | None = None


class ApprovalRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    priority: int | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    vendor_id: UUID | None = None
    department: str | None = None
    cost_center: str | None = None
    location: str | None = None
    document_type: str | None = None
    risk_level: str | None = None
    requires_po: bool | None = None
    step_number: int | None = None
    step_name: str | None = None
    execution_mode: ApprovalExecutionMode | None = None
    approver_type: ApproverType | None = None
    approver_id: UUID | None = None
    approver_role: str | None = None
    approver_group_id: UUID | None = None
    conditions: dict | None = None
    actions: list[dict] | None = None


class ApprovalGroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupMemberAdd(BaseModel):
    user_id: UUID


class PaymentOverrideRequest(BaseModel):
    reason: str = Field(min_length=1)


class InvoiceCommentCreate(BaseModel):
    body: str
    mentioned_user_ids: list[UUID] = Field(default_factory=list)


def _to_payload(model: BaseModel) -> dict:
    return model.model_dump(mode="json", exclude_unset=True)


# ============================================================
# Rules
# ============================================================

@router.get("/rules")
async def list_rules(
    scope: ApprovalRuleScope | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    rules = await ApprovalRuleService().list_rules(ctx.org_id, scope)
    return [r.model_dump(mode="json") for r in rules]


@router.post("/rules", status_code=201)
async def create_rule(
    payload: ApprovalRuleCreate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    try:
        created = await ApprovalRuleService().create_rule(
            ctx.org_id, _to_payload(payload), user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return created.model_dump(mode="json")


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: UUID,
    payload: ApprovalRuleUpdate,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    try:
        updated = await ApprovalRuleService().update_rule(
            ctx.org_id, rule_id, _to_payload(payload)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return updated.model_dump(mode="json")


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    try:
        await ApprovalRuleService().delete_rule(ctx.org_id, rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ============================================================
# Groups
# ============================================================

@router.get("/groups")
async def list_groups(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    groups = await ApprovalGroupService().list_groups(ctx.org_id)
    return [g.model_dump(mode="json") for g in groups]


@router.post("/groups", status_code=201)
async def create_group(
    payload: ApprovalGroupCreate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    try:
        created = await ApprovalGroupService().create_group(
            ctx.org_id, payload.name, payload.description, user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return created.model_dump(mode="json")


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    try:
        await ApprovalGroupService().delete_group(ctx.org_id, group_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/groups/{group_id}/members")
async def list_group_members(
    group_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    try:
        members = await ApprovalGroupService().list_members(ctx.org_id, group_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [m.model_dump(mode="json") for m in members]


@router.post("/groups/{group_id}/members", status_code=201)
async def add_group_member(
    group_id: UUID,
    payload: GroupMemberAdd,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    try:
        await ApprovalGroupService().add_member(ctx.org_id, group_id, payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "added"}


@router.delete("/groups/{group_id}/members/{user_id}", status_code=204)
async def remove_group_member(
    group_id: UUID,
    user_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    try:
        await ApprovalGroupService().remove_member(ctx.org_id, group_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/steps/{step_id}/claim")
async def claim_step(
    step_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_APPROVALS)),
):
    """
    Claims a pooled ("processing group") approval step — first
    member of the assigned group to act gets to decide it. Sets
    approver_id to the claimant so the normal decide endpoint
    (POST /approvals/{step_id}/decide) then works unchanged.
    """
    try:
        step = await ApprovalGroupService().claim_step(
            org_id=ctx.org_id, step_id=step_id, user_id=user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return step.model_dump(mode="json")


# ============================================================
# Payment authorization
# ============================================================

@router.get("/payments/queue")
async def payment_queue(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(AUTHORIZE_PAYMENTS)),
):
    return await PaymentAuthorizationService().list_queue(ctx.org_id)


@router.post("/payments/{document_id}/evaluate")
async def evaluate_payment_authorization(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(AUTHORIZE_PAYMENTS)),
):
    try:
        result = await PaymentAuthorizationService().evaluate(
            org_id=ctx.org_id, document_id=document_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.post("/payments/{document_id}/override")
async def override_payment_block(
    document_id: UUID,
    payload: PaymentOverrideRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(OVERRIDE_PAYMENT_BLOCKS)),
):
    """
    Lets a privileged user (owner, by default) force a blocked
    payment through — the video's "big bosses are annoying like
    that" override — while keeping who/when/why on the record.

    If a payment_instruction already exists for this document and
    is BLOCKED, the override also authorizes and executes it —
    otherwise an override would flip the compliance record without
    ever actually releasing the payment.
    """
    try:
        result = await PaymentAuthorizationService().override(
            org_id=ctx.org_id, document_id=document_id, actor_id=user.id, reason=payload.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    release_status = "not_started"
    instructions = PaymentInstructionService()
    rows = (await execute(instructions.repository.db.table("payment_instructions").select("id,status").eq(
        "org_id", str(ctx.org_id)
    ).eq("document_id", str(document_id)).order("created_at", desc=True).limit(1))).data
    if rows and rows[0]["status"] == PaymentInstructionStatus.BLOCKED.value:
        instruction_id = UUID(rows[0]["id"])
        try:
            await instructions.transition(
                org_id=ctx.org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.AUTHORIZED,
                actor_id=user.id, reason=f"admin override: {payload.reason}", authorized_by=str(user.id),
            )
            await instructions.execute(org_id=ctx.org_id, instruction_id=instruction_id, actor_id=user.id)
            release_status = "released_to_provider"
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Payment authorization override was recorded but release failed for document %s", document_id
            )
            raise HTTPException(
                status_code=502,
                detail="The override was recorded, but the payment was not released. Check provider configuration and payment activity before retrying.",
            ) from exc
    response = result.model_dump(mode="json")
    response["release_status"] = release_status
    return response


# ============================================================
# Comments / tagging
# ============================================================

@router.get("/documents/{document_id}/comments")
async def list_comments(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    comments = await InvoiceCommentService().list_for_document(ctx.org_id, document_id)
    return [c.model_dump(mode="json") for c in comments]


@router.post("/documents/{document_id}/comments", status_code=201)
async def add_comment(
    document_id: UUID,
    payload: InvoiceCommentCreate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    try:
        created = await InvoiceCommentService().add_comment(
            org_id=ctx.org_id,
            document_id=document_id,
            author_id=user.id,
            body=payload.body,
            mentioned_user_ids=payload.mentioned_user_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return created.model_dump(mode="json")


# ============================================================
# Payment instructions (the actual payment record — separate
# from the payment_authorizations compliance gate above)
# ============================================================

class WebhookPayload(BaseModel):
    provider_payment_id: str
    status: str
    occurred_at: str | None = None
    failure_reason: str | None = None


@router.get("/payments/{document_id}/instructions")
async def list_payment_instructions(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(AUTHORIZE_PAYMENTS)),
):
    from app.services.payment.payment_instruction_service import PaymentInstructionService as _PIS
    rows = await _PIS().repository.list_for_document(ctx.org_id, document_id)
    return [r.model_dump(mode="json") for r in rows]


class PaymentInstructionCreateRequest(BaseModel):
    payment_method: str | None = Field(default=None, max_length=40)
    scheduled_date: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


@router.post("/payments/{document_id}/instructions", status_code=201)
async def create_payment_instruction(
    document_id: UUID,
    payload: PaymentInstructionCreateRequest | None = None,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(AUTHORIZE_PAYMENTS)),
):
    """
    Manually (re)starts the payment pipeline for a document that has
    reached PAYMENT_READY — normally this happens automatically from
    BillSyncWorker; this endpoint exists for retries and for
    documents that reached PAYMENT_READY before this feature shipped.
    Idempotent on document_id.
    """
    from app.services.payment.payment_approval_service import PaymentApprovalService
    try:
        request_data = payload or PaymentInstructionCreateRequest()
        result = await PaymentApprovalService().initiate(
            org_id=ctx.org_id, document_id=document_id, requested_by=user.id,
            idempotency_key=request_data.idempotency_key,
            payment_method=request_data.payment_method,
            scheduled_date=request_data.scheduled_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.post("/payments/webhook/{org_id}")
async def payment_provider_webhook(org_id: UUID, payload: WebhookPayload):
    """Fail closed: this build has no configured signature-verifying rail.

    Do not accept a caller-supplied org ID and status as proof of payment.
    Enable this route only when a provider adapter verifies the signature
    against the original raw request body and enforces provider event IDs.
    """
    raise HTTPException(
        status_code=503,
        detail="Payment webhooks are disabled until a signature-verifying payment provider is configured.",
    )

class PaymentCancellationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.get("/payments/instructions/{instruction_id}/events")
async def list_payment_instruction_events(
    instruction_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    service = PaymentInstructionService()
    instruction = await service.repository.get(instruction_id)
    if instruction is None or str(instruction.org_id) != str(ctx.org_id):
        raise HTTPException(status_code=404, detail="Payment instruction not found.")
    events = await service.events.list_for_instruction(instruction_id)
    return [event.model_dump(mode="json") for event in events]


@router.post("/payments/instructions/{instruction_id}/cancel")
async def cancel_payment_instruction(
    instruction_id: UUID,
    payload: PaymentCancellationRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(AUTHORIZE_PAYMENTS)),
):
    try:
        result = await PaymentInstructionService().cancel(
            org_id=ctx.org_id, instruction_id=instruction_id,
            actor_id=user.id, reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.post("/payments/instructions/{instruction_id}/reconcile")
async def reconcile_payment_instruction(
    instruction_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(AUTHORIZE_PAYMENTS)),
):
    from app.services.payment.payment_instruction_service import PaymentInstructionService as _PIS
    try:
        result = await _PIS().reconcile(org_id=ctx.org_id, instruction_id=instruction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result.model_dump(mode="json")


# ============================================================
# Vendor controls: W-9 and bank-change verification (internal,
# authenticated side). The vendor-facing token side lives in
# app/routers/vendor_portal.py (no auth — token-gated).
# ============================================================

class VendorDocumentRequestCreate(BaseModel):
    request_type: VendorDocumentRequestType


class BankVerificationDecision(BaseModel):
    approve: bool
    reason: str | None = None


@router.get("/vendors/{vendor_id}/document-requests")
async def list_vendor_document_requests(
    vendor_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    from app.services.vendor.vendor_controls_service import VendorControlsService
    rows = await VendorControlsService().list_for_vendor(ctx.org_id, vendor_id)
    return [r.model_dump(mode="json") for r in rows]


@router.post("/vendors/{vendor_id}/document-requests", status_code=201)
async def create_vendor_document_request(
    vendor_id: UUID,
    payload: VendorDocumentRequestCreate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    from app.services.vendor.vendor_controls_service import VendorControlsService
    try:
        created = await VendorControlsService().request_document(
            org_id=ctx.org_id, vendor_id=vendor_id, request_type=payload.request_type, requested_by=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # created.token is the vendor-facing secret — the frontend is
    # responsible for turning this into a /vendor-portal/{token} link
    # and sending it (email) rather than displaying the raw token in
    # an internal list view going forward.
    return created.model_dump(mode="json")


@router.post("/vendors/document-requests/{request_id}/verify-bank-change")
async def verify_bank_change_request(
    request_id: UUID,
    payload: BankVerificationDecision,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(OVERRIDE_PAYMENT_BLOCKS)),
):
    """
    Verifying a bank change is gated behind the same permission as
    overriding a payment block — both are "trust this sensitive
    thing enough to let money move" decisions.
    """
    from app.services.vendor.vendor_controls_service import VendorControlsService
    try:
        result = await VendorControlsService().verify_bank_change(
            org_id=ctx.org_id, request_id=request_id, actor_id=user.id,
            approve=payload.approve, reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.post("/documents/{document_id}/create-bill", status_code=202)
async def create_bill_for_document(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    """Explicitly queue ERP bill creation; this does not authorize or release payment."""
    from app.core.supabase import get_supabase
    from app.workers.bill_sync_worker import BillSyncWorker
    db = get_supabase()
    rows = (await execute(db.table("documents").select("id,org_id,ap_enabled,ap_status,erp_bill_id").eq(
        "id", str(document_id)).eq("org_id", str(ctx.org_id)).limit(1))).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    doc = rows[0]
    if not doc.get("ap_enabled"):
        raise HTTPException(status_code=409, detail="Accounts payable is not enabled for this invoice.")
    if doc.get("erp_bill_id"):
        return {"status":"already_synced", "document_id":str(document_id), "erp_bill_id":doc["erp_bill_id"]}
    if doc.get("ap_status") != "approved":
        raise HTTPException(status_code=409, detail="Invoice must be approved before creating an ERP bill.")
    try:
        await BillSyncWorker(db=db).execute(document_id=document_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ERP bill sync failed: {str(exc)[:300]}") from exc
    refreshed = (await execute(db.table("documents").select("ap_status,erp_bill_id,erp_sync_error").eq(
        "id", str(document_id)).eq("org_id", str(ctx.org_id)).single())).data
    if not refreshed.get("erp_bill_id"):
        raise HTTPException(status_code=502, detail=refreshed.get("erp_sync_error") or "ERP did not confirm bill creation.")
    return {"status":refreshed.get("ap_status"), "document_id":str(document_id), "erp_bill_id":refreshed["erp_bill_id"], "payment_released":False}


# ============================================================
# Provider-specific accounting tax-code mappings
# ============================================================
class AccountingTaxMappingCreate(BaseModel):
    provider: str
    source_tax_rate: Decimal = Field(ge=0, le=100)
    source_tax_code: str | None = None
    external_tax_code_id: str = Field(min_length=1, max_length=200)
    external_tax_code_name: str | None = None


@router.get("/accounting-tax-mappings")
async def list_accounting_tax_mappings(
    provider: str | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    from app.core.supabase import get_supabase
    if provider and provider not in {"quickbooks", "xero"}:
        raise HTTPException(status_code=422, detail="Provider must be quickbooks or xero.")
    query = get_supabase().table("accounting_tax_code_mappings").select(
        "id,provider,source_tax_rate,source_tax_code,external_tax_code_id,external_tax_code_name,is_active,created_at,updated_at"
    ).eq("org_id", str(ctx.org_id)).order("source_tax_rate")
    if provider: query = query.eq("provider", provider)
    return (await execute(query)).data or []


@router.post("/accounting-tax-mappings", status_code=201)
async def create_accounting_tax_mapping(
    payload: AccountingTaxMappingCreate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    from app.core.supabase import get_supabase
    if payload.provider not in {"quickbooks", "xero"}:
        raise HTTPException(status_code=422, detail="Provider must be quickbooks or xero.")
    db = get_supabase()
    data = {
        "org_id": str(ctx.org_id), "provider": payload.provider,
        "source_tax_rate": str(payload.source_tax_rate), "source_tax_code": payload.source_tax_code,
        "external_tax_code_id": payload.external_tax_code_id.strip(),
        "external_tax_code_name": payload.external_tax_code_name, "created_by": str(user.id), "is_active": True,
    }
    try:
        rows = (await execute(db.table("accounting_tax_code_mappings").upsert(
            data, on_conflict="org_id,provider,source_tax_rate,source_tax_code"
        ))).data or []
    except Exception as exc:
        raise HTTPException(status_code=409, detail="Could not save mapping. Confirm the tax-mapping migration is applied and there is no conflicting mapping.") from exc
    return rows[0] if rows else {"saved": True, "provider": payload.provider, "source_tax_rate": str(payload.source_tax_rate)}


@router.delete("/accounting-tax-mappings/{mapping_id}", status_code=204)
async def deactivate_accounting_tax_mapping(
    mapping_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_AP_RULES)),
):
    from app.core.supabase import get_supabase
    rows = (await execute(get_supabase().table("accounting_tax_code_mappings").update({"is_active": False}).eq(
        "id", str(mapping_id)).eq("org_id", str(ctx.org_id)))).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Tax mapping not found.")
