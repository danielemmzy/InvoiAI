from __future__ import annotations
import logging
import asyncio
from typing import Literal
from uuid import UUID
from decimal import Decimal
from datetime import UTC, datetime
from app.core.container import get_container
from fastapi import APIRouter, Depends, HTTPException, Request, Query, File, UploadFile
from pydantic import BaseModel, Field
from app.context import OrganizationContext
from app.core.ocm import get_org_context
from app.core.permissions import VIEW_FINANCE, MANAGE_FINANCE
from app.core.config import settings
from app.core.enum.database import DocumentStatus, DocumentType, OrgRole
from app.core.auth import require_verified_user
from app.core.authorization import require_permission
from app.core.limiter import limiter
from app.core.redis import get_redis
from app.core.supabase import get_supabase
from app.services.ap.exception_service import ExceptionService
from app.services.document.document_upload_service import DuplicateDocumentError
from app.services.ap.approval_bridge import APApprovalBridge
from app.services.ap.chart_of_accounts_service import ChartOfAccountsService
from app.services.ap.chart_of_accounts_seed import seed_starter_chart_of_accounts
from app.services.ap.recovery_service import APRecoveryService, is_stale
from app.services.ap.email_address_service import manage_email_address
from app.services.audit_service import AuditService
from app.services.ap.provider.accounting_provider import (
    NoActiveAccountingProviderError,
    get_accounting_provider,
)

from app.core.enum.ap import InvoiceAPStatus
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.workers.ap_matching_worker import APMatchingWorker
from app.workers.ap_coding_worker import APCodingWorker
from app.core.enum.ap import InvoiceAPStatus
from app.services.ap.invoice_state_machine import InvoiceStateMachine


async def _run_explicit_ap_workflow(document_id: UUID) -> None:
    """Run one AP pipeline per invoice, persisting exceptions instead of hanging."""
    redis = await get_redis()
    lock = redis.lock(f"invoiai:ap:workflow:{document_id}", timeout=900, blocking=False)
    if not await lock.acquire():
        logging.getLogger(__name__).info("AP workflow already running for %s; duplicate dispatch ignored", document_id)
        return
    try:
        await APMatchingWorker().execute(document_id=document_id)

        state = InvoiceStateMachine()
        status = await state.get_status(document_id)
        if status in {InvoiceAPStatus.CODING, InvoiceAPStatus.CODING_EXCEPTION}:
            try:
                await APCodingWorker().execute(document_id=document_id)
            except Exception as exc:
                logging.getLogger(__name__).exception("AP GL coding failed for document %s", document_id)
                database = get_supabase()
                rows = database.table("documents").select("org_id,ap_status").eq("id", str(document_id)).limit(1).execute().data or []
                if rows:
                    org_id = UUID(rows[0]["org_id"])
                    current = await state.get_status(document_id)
                    if current == InvoiceAPStatus.CODING:
                        await state.transition(document_id, org_id, InvoiceAPStatus.CODING_EXCEPTION, triggered_by="worker", reason="GL coding service failed")
                    database.table("documents").update({
                        "status": "needs_review", "processing_step": "ap_coding_error",
                        "processing_message": "GL coding could not finish because a service error occurred. Your invoice and saved line data were retained. Correct any missing GL assignments, then retry the exception.",
                        "processing_progress": 85, "gl_coding_status": "needs_review",
                        "error_message": str(exc)[:500],
                    }).eq("id", str(document_id)).eq("org_id", str(org_id)).execute()
                    open_rows = database.table("invoice_exceptions").select("id").eq("org_id", str(org_id)).eq("document_id", str(document_id)).eq("exception_type", "gl_coding_required").in_("status", ["open", "in_review", "escalated"]).limit(1).execute().data or []
                    if not open_rows:
                        database.table("invoice_exceptions").insert({
                            "org_id": str(org_id), "document_id": str(document_id),
                            "exception_type": "gl_coding_required", "severity": "warning",
                            "title": "GL coding could not finish", "details": {"error": str(exc)[:500], "retryable": True},
                        }).execute()
    finally:
        try:
            await lock.release()
        except Exception:
            logging.getLogger(__name__).warning("Could not release AP workflow lock for %s", document_id, exc_info=True)


router = APIRouter(
    prefix="/ap",
    tags=["AP Automation"],
    dependencies=[Depends(require_verified_user)],
)


async def _audit_finance_change(
    ctx: OrganizationContext,
    *,
    action: str,
    resource_type: str,
    resource_id: UUID,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    """Audit financial configuration changes without failing the mutation."""
    try:
        await AuditService().log(
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
        )
    except Exception:
        logging.getLogger(__name__).exception("Failed to audit %s for %s", action, resource_id)


def _account_code_in_use(org_id: UUID, code: str, *, exclude_id: UUID | None = None) -> bool:
    query = (
        db()
        .table("chart_of_accounts")
        .select("id")
        .eq("org_id", str(org_id))
        .eq("account_code", code)
    )
    if exclude_id is not None:
        query = query.neq("id", str(exclude_id))
    return bool(query.limit(1).execute().data)

class APRunRequest(BaseModel):
    purchase_order_id: UUID | None = None
    goods_receipt_id: UUID | None = None
    match_mode: str = Field(default="auto", pattern="^(auto|non_po|two_way|three_way)$")


class ReferenceConvertRequest(BaseModel):
    purchase_order_id: UUID | None = None


ACCOUNT_TYPES = ("asset", "liability", "equity", "revenue", "expense")
AccountType = Literal["asset", "liability", "equity", "revenue", "expense"]


class ChartOfAccountCreate(BaseModel):
    account_code: str = Field(min_length=1, max_length=32)
    account_name: str = Field(min_length=1, max_length=200)
    account_type: AccountType = "expense"
    account_subtype: str | None = None
    external_id: str | None = None
    is_active: bool = True
    is_postable: bool = True


class ChartOfAccountUpdate(BaseModel):
    account_code: str | None = Field(default=None, min_length=1, max_length=32)
    account_name: str | None = Field(default=None, min_length=1, max_length=200)
    account_type: AccountType | None = None
    account_subtype: str | None = None
    is_active: bool | None = None
    is_postable: bool | None = None



def db():
    return get_supabase()


@router.post("/reference-documents/upload", status_code=202)
async def upload_ap_reference_document(
    file: UploadFile = File(...),
    reference_type: str = "purchase_order",
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Upload a PO or goods receipt as a real document, then convert it to a canonical AP record."""
    if reference_type not in {"purchase_order", "goods_receipt"}:
        raise HTTPException(422, "reference_type must be purchase_order or goods_receipt")
    if file.content_type not in set(settings.allowed_file_types):
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")
    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds the {settings.max_file_size_mb}MB limit.")
    document_type = DocumentType.PURCHASE_ORDER if reference_type == "purchase_order" else DocumentType.DELIVERY_NOTE
    try:
        document = await get_container().document_upload_service.upload(
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            filename=file.filename or reference_type,
            content_type=file.content_type,
            content=content,
            industry="general",
            document_type=document_type,
            currency="USD",
            external_metadata={"ap_reference_type": reference_type},
            allow_duplicate=False,
        )
    except DuplicateDocumentError as exc:
        # AP reference uploads are allowed to reuse an existing document.
        # The global document intake service correctly rejects duplicate files,
        # but AP should not fail when the PO/receipt already exists in the
        # workspace. Return the canonical source document so the existing
        # conversion/polling flow can continue.
        if not exc.existing_document_id:
            raise HTTPException(409, str(exc)) from exc

        existing_rows = (
            db()
            .table("documents")
            .select("id,document_type,status,processing_step,external_source_data")
            .eq("org_id", str(ctx.org_id))
            .eq("id", str(exc.existing_document_id))
            .limit(1)
            .execute()
            .data
            or []
        )
        if not existing_rows:
            raise HTTPException(409, str(exc)) from exc

        existing = existing_rows[0]
        existing_type = existing.get("document_type")
        expected_type = document_type.value
        if existing_type not in {expected_type, None}:
            raise HTTPException(409, "This file already exists as a different document type in this workspace.")

        # Preserve the AP reference role on an existing source document so
        # conversion knows whether it represents a PO or goods receipt.
        metadata = existing.get("external_source_data") or {}
        if metadata.get("ap_reference_type") != reference_type:
            metadata = {**metadata, "ap_reference_type": reference_type}
            db().table("documents").update({"external_source_data": metadata}).eq(
                "org_id", str(ctx.org_id)
            ).eq("id", str(exc.existing_document_id)).execute()

        document_id = UUID(str(existing["id"]))
        return {
            "document_id": str(document_id),
            "reference_type": reference_type,
            "status": "reused",
            "reused": True,
        }
    if document.status == DocumentStatus.QUARANTINED:
        raise HTTPException(
            422,
            "Attachment quarantined by the security scanner and will not be processed.",
        )

    task = asyncio.create_task(
        get_container().ocr_worker.execute(document_id=document.id),
        name=f"ap-reference-ocr:{document.id}",
    )
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    return {"document_id": str(document.id), "reference_type": reference_type, "status": "processing"}


@router.post("/reference-documents/{source_document_id}/convert")
async def convert_ap_reference_document(
    source_document_id: UUID,
    body: ReferenceConvertRequest | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Convert a processed PO/delivery-note document into a canonical selectable AP record."""
    database = db()
    source_rows = database.table("documents").select("*").eq("org_id", str(ctx.org_id)).eq("id", str(source_document_id)).limit(1).execute().data or []
    if not source_rows:
        raise HTTPException(404, "Reference document not found")
    source = source_rows[0]
    reference_type = (source.get("external_source_data") or {}).get("ap_reference_type")
    if reference_type not in {"purchase_order", "goods_receipt"}:
        reference_type = "purchase_order" if source.get("document_type") == DocumentType.PURCHASE_ORDER.value else "goods_receipt"
    if source.get("processing_step") in {"ocr", "extraction", "reading", "classification"} or source.get("status") in {"ocr_running", "processing"}:
        return {"ready": False, "status": "processing", "source_document_id": str(source_document_id)}

    lines = database.table("document_line_items").select("*").eq("org_id", str(ctx.org_id)).eq("document_id", str(source_document_id)).order("position").execute().data or []
    vendor_id = source.get("vendor_id")
    total = source.get("total_amount") or source.get("subtotal") or 0
    currency = source.get("currency") or "USD"
    number = source.get("document_number") or source.get("file_name") or f"REF-{str(source_document_id)[:8]}"
    if reference_type == "purchase_order":
        existing = database.table("purchase_orders").select("id").eq("org_id", str(ctx.org_id)).eq("po_number", str(number)).limit(1).execute().data or []
        if existing:
            return {"ready": True, "reference_type": reference_type, "source_document_id": str(source_document_id), "purchase_order_id": existing[0]["id"]}
        metadata = {"source_document_id": str(source_document_id), "source_file_name": source.get("file_name"), "line_items": [{k: v for k, v in line.items() if k in {"description", "quantity", "unit_price", "amount", "sku", "product_code", "position"}} for line in lines]}
        created = database.table("purchase_orders").insert({
            "org_id": str(ctx.org_id), "vendor_id": vendor_id, "po_number": str(number),
            "amount": total, "currency": currency, "description": source.get("notes") or source.get("vendor_name"),
            "issued_date": source.get("document_date"), "expiry_date": source.get("due_date"),
            "is_open": True, "created_by": str(ctx.user_id), "metadata": metadata,
        }).execute().data or []
        if not created: raise HTTPException(500, "Could not create purchase order")
        return {"ready": True, "reference_type": reference_type, "source_document_id": str(source_document_id), "purchase_order_id": created[0]["id"]}

    po_id = (body or ReferenceConvertRequest()).purchase_order_id
    if not po_id:
        raise HTTPException(422, "purchase_order_id is required when converting a goods receipt")
    po = database.table("purchase_orders").select("id,vendor_id").eq("org_id", str(ctx.org_id)).eq("id", str(po_id)).limit(1).execute().data or []
    if not po: raise HTTPException(404, "Purchase order not found")
    existing = database.table("goods_receipts").select("id").eq("org_id", str(ctx.org_id)).eq("external_id", str(source_document_id)).limit(1).execute().data or []
    if existing:
        return {"ready": True, "reference_type": reference_type, "source_document_id": str(source_document_id), "goods_receipt_id": existing[0]["id"]}
    receipt = database.table("goods_receipts").insert({
        "org_id": str(ctx.org_id), "purchase_order_id": str(po_id), "vendor_id": po[0].get("vendor_id") or vendor_id,
        "receipt_number": str(number), "received_at": source.get("document_date") or datetime.now(UTC).isoformat(),
        "received_by": str(ctx.user_id), "status": "confirmed", "source": "uploaded_document", "external_id": str(source_document_id),
        "notes": source.get("file_name"),
    }).execute().data or []
    if not receipt: raise HTTPException(500, "Could not create goods receipt")
    receipt_id = receipt[0]["id"]
    if lines:
        database.table("goods_receipt_lines").insert([{
            "goods_receipt_id": receipt_id,
            "description": line.get("description"), "sku": line.get("sku") or line.get("product_code"),
            "quantity_ordered": line.get("quantity"), "quantity_received": line.get("quantity") or 0,
            "quantity_accepted": line.get("quantity") or 0, "unit_price": line.get("unit_price"),
            "notes": f"Source document {source_document_id}",
        } for line in lines]).execute()
    return {"ready": True, "reference_type": reference_type, "source_document_id": str(source_document_id), "goods_receipt_id": receipt_id}


@router.get("/matching/receipts/{purchase_order_id}")
async def matching_receipts(
    purchase_order_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    return await __import__("app.repositories.ap.goods_receipt_repository", fromlist=["GoodsReceiptRepository"]).GoodsReceiptRepository().list_by_po(ctx.org_id, purchase_order_id)


@router.get("/matching/purchase-orders")
async def matching_purchase_orders(
    vendor_id: UUID | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    rows = db().table("purchase_orders").select("*, vendors(name)").eq("org_id", str(ctx.org_id)).eq("is_open", True).order("issued_date", desc=True).limit(100).execute().data or []
    if vendor_id:
        rows = [r for r in rows if str(r.get("vendor_id")) == str(vendor_id)]
    return rows


@router.get("/exceptions")
async def list_exceptions(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    rows = await ExceptionService().list_open(ctx.org_id)
    payload = [r.model_dump(mode="json") for r in rows]
    document_ids = list({str(row.get("document_id")) for row in payload if row.get("document_id")})
    documents = db().table("documents").select("id,document_number,vendor_name,file_name,total_amount,currency,ap_status").eq("org_id", str(ctx.org_id)).in_("id", document_ids).execute().data or [] if document_ids else []
    by_id = {str(row["id"]): row for row in documents}
    for row in payload:
        row["document"] = by_id.get(str(row.get("document_id")))
    return payload


@router.get("/exceptions/{document_id}")
async def document_exceptions(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    rows = await ExceptionService().list_for_document(ctx.org_id, document_id)
    return [r.model_dump(mode="json") for r in rows]


@router.post("/exceptions/{exception_id}/resolve")
async def resolve_exception(
    exception_id: UUID,
    body: dict,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    try:
        result = await ExceptionService().resolve(
            ctx.org_id, exception_id, ctx.user_id, body.get("note", "") or "", False
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"resolved": bool(result.get("updated", True)), **result}


@router.post("/exceptions/{exception_id}/waive")
async def waive_exception(
    exception_id: UUID,
    body: dict,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    try:
        result = await ExceptionService().resolve(
            ctx.org_id, exception_id, ctx.user_id, body.get("note", "") or "", True
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"waived": bool(result.get("updated", True)), **result}


@router.get("/codings/{document_id}")
async def document_codings(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    rows = (
        db()
        .table("invoice_codings")
        .select("*")
        .eq("org_id", str(ctx.org_id))
        .eq("document_id", str(document_id))
        .order("created_at")
        .execute()
        .data
        or []
    )
    return rows


@router.post("/codings/{document_id}/approve")
async def approve_codings(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    rows = (
        db()
        .table("invoice_codings")
        .select("id,status,gl_account_id,line_item_id")
        .eq("org_id", str(ctx.org_id))
        .eq("document_id", str(document_id))
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(404, "No codings found")
    line_items = db().table("document_line_items").select("id").eq(
        "org_id", str(ctx.org_id)
    ).eq("document_id", str(document_id)).execute().data or []
    coding_line_ids = {str(row.get("line_item_id")) for row in rows if row.get("line_item_id")}
    if any(str(line.get("id")) not in coding_line_ids for line in line_items):
        raise HTTPException(409, "Assign an active postable account to every invoice line before approving coding.")
    for row in rows:
        account = db().table("chart_of_accounts").select(
            "id,is_active,is_postable"
        ).eq("org_id", str(ctx.org_id)).eq(
            "id", str(row.get("gl_account_id"))
        ).limit(1).execute().data or []
        if not account or not account[0].get("is_active") or not account[0].get("is_postable"):
            raise HTTPException(409, "Assign an active postable account to every invoice line before approving coding.")
    if any(
        r.get("status") not in {"needs_review", "auto_coded", "approved"} for r in rows
    ):
        raise HTTPException(409, "Coding is not ready for approval")
    db().table("invoice_codings").update(
        {"status": "approved", "approved_by": str(ctx.user_id)}
    ).eq("org_id", str(ctx.org_id)).eq("document_id", str(document_id)).execute()
    db().table("documents").update({"gl_coding_status": "approved"}).eq(
        "org_id", str(ctx.org_id)
    ).eq("id", str(document_id)).execute()
    db().table("invoice_exceptions").update(
        {
            "status": "resolved",
            "resolved_by": str(ctx.user_id),
            "resolved_at": "now()",
            "resolution_note": "Coding approved by reviewer",
        }
    ).eq("org_id", str(ctx.org_id)).eq("document_id", str(document_id)).eq(
        "exception_type", "gl_coding_required"
    ).eq(
        "status", "open"
    ).execute()
    analysis = (
        db()
        .table("document_analyses")
        .select("id")
        .eq("org_id", str(ctx.org_id))
        .eq("document_id", str(document_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    analysis_id = UUID(analysis[0]["id"]) if analysis else None
    await APApprovalBridge().create_workflow(
        org_id=ctx.org_id,
        document_id=document_id,
        analysis_id=analysis_id,
        initiated_by=ctx.user_id,
    )
    return {"approved": True, "routed_to_approval": True}


@router.put("/codings/{document_id}/line/{line_item_id}")
async def save_line_coding(
    document_id: UUID,
    line_item_id: UUID,
    body: LineCodingSave,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Save or update a manual GL coding for a single invoice line.

    The upsert key is (document_id, line_item_id). Source is forced to 'manual',
    status to 'approved', confidence to 100. This mirrors the reviewer workflow
    and ensures manual corrections survive re-coding attempts.
    """
    database = db()
    account = (
        database.table("chart_of_accounts")
        .select("id,account_code,account_name,is_postable,is_active")
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(body.gl_account_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not account:
        raise HTTPException(404, "GL account not found")
    if not account[0].get("is_postable"):
        raise HTTPException(409, "Selected account is not postable")
    if not account[0].get("is_active"):
        raise HTTPException(409, "Selected account is inactive")

    payload = {
        "org_id": str(ctx.org_id),
        "document_id": str(document_id),
        "line_item_id": str(line_item_id),
        "gl_account_id": str(body.gl_account_id),
        "gl_account_code": account[0]["account_code"],
        "gl_account_name": account[0]["account_name"],
        "amount": body.amount,
        "source": "manual",
        "status": "approved",
        "confidence": 100,
        "created_by": str(ctx.user_id),
    }

    existing = (
        database.table("invoice_codings")
        .select("id,gl_account_id,status")
        .eq("org_id", str(ctx.org_id))
        .eq("document_id", str(document_id))
        .eq("line_item_id", str(line_item_id))
        .limit(1)
        .execute()
        .data
        or []
    )

    changed_approved_coding = bool(
        existing
        and existing[0].get("status") == "approved"
        and existing[0].get("gl_account_id") != str(body.gl_account_id)
    )
    if existing:
        if changed_approved_coding:
            payload.update({"status": "needs_review", "approved_by": None})
        database.table("invoice_codings").update(payload).eq("id", existing[0]["id"]).execute()
    else:
        database.table("invoice_codings").insert(payload).execute()

    # Also persist on the line item for immediate UI feedback
    database.table("document_line_items").update({
        "gl_account_id": str(body.gl_account_id),
        "gl_account_code": account[0]["account_code"],
        "gl_account_name": account[0]["account_name"],
    }).eq("org_id", str(ctx.org_id)).eq("id", str(line_item_id)).execute()

    if changed_approved_coding:
        workflows = database.table("approval_workflows").select("id,status").eq(
            "org_id", str(ctx.org_id)
        ).eq("document_id", str(document_id)).execute().data or []
        for workflow in workflows:
            if workflow.get("status") in {"pending", "in_review", "approved"}:
                database.table("approval_workflows").update({"status": "cancelled"}).eq(
                    "org_id", str(ctx.org_id)
                ).eq("id", str(workflow["id"])).execute()
        database.table("documents").update({
            "status": "needs_review",
            "ap_status": "coding",
            "gl_coding_status": "needs_review",
        }).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()
        await _audit_finance_change(
            ctx,
            action="ap.gl_coding_changed_after_approval",
            resource_type="document",
            resource_id=document_id,
            old_values={"gl_account_id": existing[0].get("gl_account_id")},
            new_values={"gl_account_id": str(body.gl_account_id), "approval_revoked": True},
        )

    return {"saved": True, "gl_account": account[0]}


@router.post("/coding-rules")
async def create_coding_rule(
    body: CodingRuleCreate,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Create a coding rule from a reviewer's manual assignment (save-as-rule).

    The rule matches future lines by vendor + description pattern (or SKU),
    and assigns the same GL account + dimensions.
    """
    database = db()
    account = (
        database.table("chart_of_accounts")
        .select("id,is_postable,is_active")
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(body.gl_account_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not account:
        raise HTTPException(404, "GL account not found")
    if not account[0].get("is_postable"):
        raise HTTPException(409, "Selected account is not postable")
    if not account[0].get("is_active"):
        raise HTTPException(409, "Selected account is inactive")

    payload = {
        "org_id": str(ctx.org_id),
        "name": body.name,
        "description": body.description,
        "vendor_id": str(body.vendor_id) if body.vendor_id else None,
        "description_pattern": body.description_pattern,
        "sku_pattern": body.sku_pattern,
        "gl_account_id": str(body.gl_account_id),
        "department_id": str(body.department_id) if body.department_id else None,
        "cost_center_id": str(body.cost_center_id) if body.cost_center_id else None,
        "project_id": str(body.project_id) if body.project_id else None,
        "tax_code_id": str(body.tax_code_id) if body.tax_code_id else None,
        "priority": body.priority or 100,
        "is_active": True,
        "created_by": str(ctx.user_id),
    }

    inserted = database.table("coding_rules").insert(payload).execute()
    return inserted.data[0] if inserted.data else {"created": False}


class LineCodingSave(BaseModel):
    gl_account_id: UUID
    amount: Decimal | None = None


class CodingRuleCreate(BaseModel):
    name: str
    description: str | None = None
    vendor_id: UUID | None = None
    description_pattern: str | None = None
    sku_pattern: str | None = None
    gl_account_id: UUID
    department_id: UUID | None = None
    cost_center_id: UUID | None = None
    project_id: UUID | None = None
    tax_code_id: UUID | None = None
    priority: int | None = 100


@router.get("/coding-rules")
async def list_coding_rules(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    """List coding rules for the organization."""
    rules = (
        db()
        .table("coding_rules")
        .select("*")
        .eq("org_id", str(ctx.org_id))
        .order("priority", desc=False)
        .execute()
        .data
        or []
    )
    return rules


@router.get("/chart-of-accounts")
async def chart_of_accounts(
    include_inactive: bool = Query(False),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    return await ChartOfAccountsService().list(ctx.org_id, active_only=not include_inactive)


@router.post("/chart-of-accounts/seed")
async def seed_chart_of_accounts(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Load a standard starter chart for an organization that has none.

    Additive and idempotent: existing account codes are never modified.
    """
    result = await seed_starter_chart_of_accounts(ctx.org_id)
    await ChartOfAccountsService().invalidate(ctx.org_id)
    if result.get("created"):
        await _audit_finance_change(
            ctx,
            action="ap.chart_of_accounts_seeded",
            resource_type="organization",
            resource_id=ctx.org_id,
            new_values=result,
        )
    return result


@router.patch("/chart-of-accounts/{account_id}")
async def update_account(
    account_id: UUID,
    body: ChartOfAccountUpdate,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    current = (
        db()
        .table("chart_of_accounts")
        .select("*")
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(account_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not current:
        raise HTTPException(404, "Account not found.")

    editable = body.model_dump(exclude_unset=True)
    if not editable:
        raise HTTPException(400, "No editable fields supplied.")

    for key in ("account_code", "account_name"):
        if key in editable:
            value = (editable[key] or "").strip()
            if not value:
                raise HTTPException(400, f"{key} cannot be empty.")
            editable[key] = value

    if "account_type" in editable and editable["account_type"] not in ACCOUNT_TYPES:
        raise HTTPException(400, "account_type must be one of: " + ", ".join(ACCOUNT_TYPES))
    if "account_code" in editable and _account_code_in_use(
        ctx.org_id, editable["account_code"], exclude_id=account_id
    ):
        raise HTTPException(409, f"Account code {editable['account_code']} already exists.")

    rows = (
        db()
        .table("chart_of_accounts")
        .update(editable)
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(account_id))
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(404, "Account not found.")
    await ChartOfAccountsService().invalidate(ctx.org_id)
    await _audit_finance_change(
        ctx,
        action="ap.chart_of_account_updated",
        resource_type="chart_of_account",
        resource_id=account_id,
        old_values={key: current[0].get(key) for key in editable},
        new_values=editable,
    )
    return rows[0]


@router.delete("/chart-of-accounts/{account_id}")
async def deactivate_account(
    account_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Soft-deactivate an account; historical codings keep their reference."""
    current = (
        db()
        .table("chart_of_accounts")
        .select("id,account_code,account_name,is_active")
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(account_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not current:
        raise HTTPException(404, "Account not found.")

    rows = (
        db()
        .table("chart_of_accounts")
        .update({"is_active": False})
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(account_id))
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(404, "Account not found.")
    await ChartOfAccountsService().invalidate(ctx.org_id)
    await _audit_finance_change(
        ctx,
        action="ap.chart_of_account_deactivated",
        resource_type="chart_of_account",
        resource_id=account_id,
        old_values={"is_active": current[0].get("is_active")},
        new_values={"is_active": False},
    )
    return {"id": str(account_id), "is_active": False}


@router.post("/chart-of-accounts/sync")
@limiter.limit("5/minute")
async def sync_chart_of_accounts(
    request: Request,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Import the active accounting provider's Chart of Accounts."""
    redis = await get_redis()
    lock = redis.lock(f"invoiai:coa:sync:{ctx.org_id}", timeout=600, blocking=False)
    if not await lock.acquire():
        raise HTTPException(
            status_code=409, detail="Chart of Accounts sync is already running."
        )
    try:
        try:
            provider = await get_accounting_provider(ctx.org_id, db())
            result = await provider.sync_chart_of_accounts(org_id=ctx.org_id)
        except NoActiveAccountingProviderError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Chart of Accounts sync failed", exc_info=exc
            )
            raise HTTPException(
                status_code=502,
                detail="Chart of Accounts sync failed. Please retry shortly.",
            ) from exc

        return {
            "provider": provider.name,
            "status": "completed",
            **result,
        }
    finally:
        try:
            await lock.release()
        except Exception:
            pass


@router.post("/chart-of-accounts")
async def create_account(
    body: ChartOfAccountCreate,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    account_code = body.account_code.strip()
    account_name = body.account_name.strip()
    if not account_code or not account_name:
        raise HTTPException(400, "account_code and account_name are required")
    if _account_code_in_use(ctx.org_id, account_code):
        raise HTTPException(409, f"Account code {account_code} already exists.")

    payload = {
        "org_id": str(ctx.org_id),
        "account_code": account_code,
        "account_name": account_name,
        "account_type": body.account_type,
        "account_subtype": body.account_subtype,
        "external_id": body.external_id,
        "is_active": body.is_active,
        "is_postable": body.is_postable,
        "source": "manual",
    }
    result = db().table("chart_of_accounts").insert(payload).execute().data[0]
    await ChartOfAccountsService().invalidate(ctx.org_id)
    await _audit_finance_change(
        ctx,
        action="ap.chart_of_account_created",
        resource_type="chart_of_account",
        resource_id=UUID(result["id"]),
        new_values=payload,
    )
    return result


@router.post("/coding-rules")
async def create_coding_rule(
    body: dict,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    payload = dict(body)
    payload["org_id"] = str(ctx.org_id)
    payload["created_by"] = str(ctx.user_id)
    return db().table("coding_rules").insert(payload).execute().data[0]


@router.get("/email-address")
async def get_email_address(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    rows = (
        db()
        .table("ap_email_intake_addresses")
        .select("*")
        .eq("org_id", str(ctx.org_id))
        .eq("is_active", True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else {"configured": False}


@router.post("/email-address")
async def create_email_address(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    if ctx.role not in {OrgRole.OWNER, OrgRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Only workspace administrators can manage the forwarding address.")
    return manage_email_address(
        db(), org_id=ctx.org_id, user_id=ctx.user_id,
        domain=settings.ap_email_inbound_domain,
    )


@router.post("/email-address/rotate")
async def rotate_email_address(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    if ctx.role not in {OrgRole.OWNER, OrgRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Only workspace administrators can rotate the forwarding address.")
    return manage_email_address(
        db(), org_id=ctx.org_id, user_id=ctx.user_id,
        domain=settings.ap_email_inbound_domain, rotate=True,
    )


@router.post("/documents/{document_id}/prepare", status_code=202)
async def prepare_ap_document(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Ensure the invoice has the structured fields required by AP matching.

    Existing Document Intelligence results are reused. Otherwise this endpoint
    runs only OCR/extraction/classification; it does not create a full
    document_analyses record or run the expensive intelligence modules.
    """
    database = db()
    rows = (
        database.table("documents")
        .select("id,document_type,intelligence_status,document_number,vendor_id,total_amount,currency")
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(document_id))
        .limit(1)
        .execute().data or []
    )
    if not rows:
        raise HTTPException(404, "Document not found")
    document = rows[0]
    if document.get("document_type") != "invoice":
        raise HTTPException(409, "Only invoice documents can be prepared for AP.")

    line_rows = (
        database.table("document_line_items")
        .select("id")
        .eq("org_id", str(ctx.org_id))
        .eq("document_id", str(document_id))
        .limit(1)
        .execute().data or []
    )
    fields_ready = bool(
        document.get("document_number")
        and document.get("vendor_id")
        and document.get("total_amount") is not None
        and document.get("currency")
        and line_rows
    )
    if fields_ready:
        return {
            "ready": True,
            "queued": False,
            "mode": "reused",
            "document_id": str(document_id),
        }

    intelligence_status = document.get("intelligence_status") or "not_requested"
    if intelligence_status in {"queued", "processing"}:
        return {
            "ready": False,
            "queued": False,
            "mode": "intelligence_in_progress",
            "document_id": str(document_id),
            "intelligence_status": intelligence_status,
        }

    await get_container().document_repository.update_processing_state(
        document_id,
        step="ap_extraction_queued",
        message="Preparing invoice fields for Accounts Payable",
        progress=5,
    )
    # AP preparation must not mark the document as having full AI intelligence.
    await get_container().document_repository.update(
        document_id,
        {"error_message": None},
    )
    task = asyncio.create_task(
        get_container().ocr_worker.execute(document_id=document_id, mode="ap"),
        name=f"ap-extraction:{document_id}",
    )
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    return {
        "ready": False,
        "queued": True,
        "mode": "ap_extraction",
        "document_id": str(document_id),
    }


@router.post("/documents/{document_id}/select")
async def select_ap_invoice(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    row = db().table("documents").select("id,document_type,ap_enabled,ap_status").eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).limit(1).execute().data or []
    if not row:
        raise HTTPException(404, "Document not found")
    if row[0].get("document_type") != "invoice":
        raise HTTPException(409, "Only invoices can be selected for AP.")
    values = {"ap_enabled": True}
    if not row[0].get("ap_status"):
        values["ap_status"] = InvoiceAPStatus.RECEIVED.value
    db().table("documents").update(values).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()
    return {"selected": True, "document_id": str(document_id), "ap_enabled": True, "ap_status": values.get("ap_status", row[0].get("ap_status"))}


async def _prepare_invoice_for_ap(document_id: UUID) -> None:
    """Prepare only the structured invoice data AP matching needs.

    This is intentionally not Document Intelligence and never creates a
    document analysis record. It is invoked only after the user explicitly
    starts AP automation. If the document was still ``unknown``, this light
    pass also classifies it. AP continues only when the result is an invoice.
    """
    await get_container().ocr_worker.execute(document_id=document_id, mode="ap")

    row = (
        db()
        .table("documents")
        .select("document_type")
        .eq("id", str(document_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    detected_type = (row[0].get("document_type") if row else None) or "unknown"
    if detected_type != "invoice":
        message = (
            f"AP automation stopped because this document was recognized as "
            f"{detected_type.replace('_', ' ')}, not an invoice."
        )
        db().table("documents").update({
            "ap_enabled": False,
            "ap_status": InvoiceAPStatus.MATCH_EXCEPTION.value,
            "match_status": "exception",
            "processing_step": "ap_type_check",
            "processing_message": message,
            "processing_progress": 100,
            "error_message": message,
        }).eq("id", str(document_id)).execute()
        return

    await _run_explicit_ap_workflow(document_id)


@router.post("/documents/{document_id}/run")
async def run_ap(
    document_id: UUID,
    body: APRunRequest | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Explicitly enroll an invoice in the AP automation workflow.

    Normal document uploads never enter AP automatically. This endpoint
    is the user-controlled entry point for AP matching and coding.
    The AP workflow is dispatched immediately as a background event. The cron
    sweeper only resumes documents that are already in progress; it never
    enrolls a new invoice.
    """
    database = db()
    row = (
        database
        .table("documents")
        .select("id,org_id,document_type,ap_enabled,ap_status,updated_at,purchase_order_id,goods_receipt_id,ap_match_mode,human_review_status")
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(document_id))
        .limit(1)
        .execute()
        .data
    )

    if not row:
        raise HTTPException(404, "Document not found")

    document = row[0]
    # An upload may legitimately still be ``unknown`` because upload itself
    # performs no OCR/AI. In that case AP is allowed to perform its own light
    # extraction/classification. Known non-invoices (POs, receipts, etc.) are
    # rejected before entering the invoice AP workflow.
    if document.get("document_type") not in {"invoice", "unknown", None}:
        raise HTTPException(409, "Only invoice documents can be processed through Accounts Payable.")

    request = body or APRunRequest()

    line_rows = database.table("document_line_items").select("id").eq("org_id", str(ctx.org_id)).eq("document_id", str(document_id)).limit(1).execute().data or []
    current_invoice = database.table("documents").select("vendor_id,total_amount,currency,document_number").eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).limit(1).execute().data or []
    fields_ready = bool(
        document.get("document_type") == "invoice"
        and current_invoice
        and current_invoice[0].get("document_number")
        and current_invoice[0].get("total_amount") is not None
        and current_invoice[0].get("currency")
        and line_rows
    )

    if request.match_mode == "non_po" and (request.purchase_order_id or request.goods_receipt_id):
        raise HTTPException(422, "Non-PO processing cannot include a purchase order or goods receipt.")
    if request.match_mode in {"two_way", "three_way"} and not request.purchase_order_id:
        raise HTTPException(422, "A purchase order is required for 2-way or 3-way matching.")
    if request.match_mode == "three_way" and not request.goods_receipt_id:
        raise HTTPException(422, "A goods receipt is required for 3-way matching.")

    # Validate all selected AP records belong to the same workspace.
    if request.purchase_order_id:
        po = database.table("purchase_orders").select("id,vendor_id,currency,is_open").eq("org_id", str(ctx.org_id)).eq("id", str(request.purchase_order_id)).limit(1).execute().data or []
        if not po:
            raise HTTPException(404, "Purchase order not found.")
    if request.goods_receipt_id:
        receipt = database.table("goods_receipts").select("id,purchase_order_id,status").eq("org_id", str(ctx.org_id)).eq("id", str(request.goods_receipt_id)).limit(1).execute().data or []
        if not receipt:
            raise HTTPException(404, "Goods receipt not found.")
        if request.purchase_order_id and str(receipt[0].get("purchase_order_id")) != str(request.purchase_order_id):
            raise HTTPException(422, "The goods receipt does not belong to the selected purchase order.")
        if request.match_mode == "three_way" and receipt[0].get("status") not in {"confirmed", "complete"}:
            raise HTTPException(422, "The selected goods receipt must be confirmed or complete for 3-way matching.")

    database.table("documents").update({
        "purchase_order_id": str(request.purchase_order_id) if request.purchase_order_id else None,
        "goods_receipt_id": str(request.goods_receipt_id) if request.goods_receipt_id else None,
        "ap_match_mode": request.match_mode,
    }).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()

    if not fields_ready:
        database.table("documents").update({
            "ap_enabled": True,
            "match_status": "pending",
            "gl_coding_status": "pending",
            "ap_status": InvoiceAPStatus.VALIDATING.value,
            "processing_step": "ap_preparing",
            "processing_message": "Preparing invoice data for Accounts Payable",
            "processing_progress": 10,
        }).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()
        asyncio.create_task(_prepare_invoice_for_ap(document_id), name=f"ap-prepare:{document_id}")
        return {"queued": True, "ap_enabled": True, "ap_status": InvoiceAPStatus.VALIDATING.value, "document_id": str(document_id), "match_mode": request.match_mode, "preparing": True}

    if document.get("ap_enabled"):
        previous_mode = document.get("ap_match_mode")
        previous_po = document.get("purchase_order_id")
        previous_receipt = document.get("goods_receipt_id")
        context_changed = (
            previous_mode != request.match_mode
            or str(previous_po or "") != str(request.purchase_order_id or "")
            or str(previous_receipt or "") != str(request.goods_receipt_id or "")
        )
        status = document.get("ap_status")
        if context_changed:
            # Changing matching inputs is an explicit restart. Keep it auditable and
            # reset progress only for this new context, never on an accidental repeat.
            database.table("documents").update({
                "ap_enabled": True, "match_status": "pending", "gl_coding_status": "pending",
                "ap_status": InvoiceAPStatus.VALIDATING.value,
                "processing_step": "ap_validating",
                "processing_message": "Validating invoice and selected matching context…",
                "processing_progress": 10, "error_message": None,
            }).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()
            asyncio.create_task(_run_explicit_ap_workflow(document_id), name=f"ap-workflow:{document_id}")
            return {"queued": True, "ap_enabled": True, "ap_status": InvoiceAPStatus.VALIDATING.value, "document_id": str(document_id), "purchase_order_id": request.purchase_order_id, "goods_receipt_id": request.goods_receipt_id, "match_mode": request.match_mode}

        # Idempotent repeat: do not clear saved state or dispatch another worker
        # unless the in-progress row is older than the recovery lease.
        if status in {InvoiceAPStatus.VALIDATING.value, InvoiceAPStatus.MATCHING.value, InvoiceAPStatus.CODING.value}:
            stale = is_stale(
                status,
                document.get("updated_at"),
                now=datetime.now(UTC),
                lease_seconds=settings.ap_recovery_lease_seconds,
            )
            if not stale:
                return {"queued": False, "in_progress": True, "ap_enabled": True, "ap_status": status, "document_id": str(document_id), "purchase_order_id": request.purchase_order_id, "goods_receipt_id": request.goods_receipt_id, "match_mode": request.match_mode}

            # A user explicitly asked again and the row has not moved for a full
            # lease: treat it as abandoned and resume from the current step.
            await APRecoveryService(database).clear(document_id)
            database.table("documents").update({"error_message": None}).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()
            asyncio.create_task(_run_explicit_ap_workflow(document_id), name=f"ap-workflow:{document_id}")
            return {"queued": True, "recovered": True, "ap_enabled": True, "ap_status": status, "document_id": str(document_id), "purchase_order_id": request.purchase_order_id, "goods_receipt_id": request.goods_receipt_id, "match_mode": request.match_mode}
        if status in {InvoiceAPStatus.MATCH_EXCEPTION.value, InvoiceAPStatus.CODING_EXCEPTION.value, InvoiceAPStatus.ON_HOLD.value}:
            open_exceptions = (
                database.table("invoice_exceptions")
                .select("id")
                .eq("org_id", str(ctx.org_id))
                .eq("document_id", str(document_id))
                .in_("status", ["open", "in_review", "escalated"])
                .limit(1)
                .execute()
                .data
                or []
            )
            # An automated recovery failure has no exception row and nothing for a
            # reviewer to correct. An explicit retry restarts the failed step
            # instead of leaving the invoice permanently blocked. Human states such
            # as on_hold and real business exceptions still require resolution.
            if not open_exceptions and status != InvoiceAPStatus.ON_HOLD.value:
                await APRecoveryService(database).clear(document_id)
                restart_from_matching = status == InvoiceAPStatus.MATCH_EXCEPTION.value
                target = (
                    InvoiceAPStatus.VALIDATING
                    if restart_from_matching
                    else InvoiceAPStatus.CODING
                )
                database.table("documents").update({
                    "match_status": "pending",
                    "gl_coding_status": "pending",
                    "processing_step": "ap_validating" if restart_from_matching else "ap_coding",
                    "processing_message": "Retrying Accounts Payable after an abandoned run…",
                    "processing_progress": 10 if restart_from_matching else 70,
                    "error_message": None,
                }).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()
                await InvoiceStateMachine(database).transition(
                    document_id,
                    ctx.org_id,
                    target,
                    actor_id=ctx.user_id,
                    triggered_by="user",
                    reason="Explicit retry after an abandoned AP workflow",
                )
                asyncio.create_task(_run_explicit_ap_workflow(document_id), name=f"ap-workflow:{document_id}")
                return {"queued": True, "recovered": True, "ap_enabled": True, "ap_status": target.value, "document_id": str(document_id), "purchase_order_id": request.purchase_order_id, "goods_receipt_id": request.goods_receipt_id, "match_mode": request.match_mode}
            return {"queued": False, "requires_resolution": True, "ap_enabled": True, "ap_status": status, "document_id": str(document_id), "purchase_order_id": request.purchase_order_id, "goods_receipt_id": request.goods_receipt_id, "match_mode": request.match_mode}
        return {"queued": False, "ap_enabled": True, "ap_status": status, "document_id": str(document_id), "purchase_order_id": request.purchase_order_id, "goods_receipt_id": request.goods_receipt_id, "match_mode": request.match_mode}

    # Mark the document as explicitly enrolled in AP first.
    database.table("documents").update({
        "ap_enabled": True,
        "match_status": "pending",
        "gl_coding_status": "pending",
        "processing_step": "ap_validating",
        "processing_message": "Validating invoice and selected matching context…",
        "processing_progress": 10,
        "error_message": None,
    }).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()

    # Use the canonical state machine so the transition is audited.
    

    state = InvoiceStateMachine(database)
    await state.transition(
        document_id,
        ctx.org_id,
        InvoiceAPStatus.VALIDATING,
        actor_id=ctx.user_id,
        triggered_by="user",
        reason="User explicitly started Accounts Payable workflow",
    )

    asyncio.create_task(_run_explicit_ap_workflow(document_id), name=f"ap-workflow:{document_id}")

    return {
        "queued": True,
        "ap_enabled": True,
        "ap_status": InvoiceAPStatus.VALIDATING.value,
        "document_id": str(document_id),
        "purchase_order_id": request.purchase_order_id,
        "goods_receipt_id": request.goods_receipt_id,
        "match_mode": request.match_mode,
    }


@router.post("/documents/{document_id}/submit-for-approval")
async def submit_ap_for_approval(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Explicit control gate: only submit after matching and GL coding are complete."""
    database = db()
    rows = database.table("documents").select("id,ap_status,gl_coding_status,ap_enabled").eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).limit(1).execute().data or []
    if not rows:
        raise HTTPException(404, "Invoice not found.")
    document = rows[0]
    if not document.get("ap_enabled"):
        raise HTTPException(409, "Start AP automation before submitting this invoice.")
    if document.get("ap_status") == InvoiceAPStatus.AWAITING_APPROVAL.value:
        return {"submitted": True, "ap_status": InvoiceAPStatus.AWAITING_APPROVAL.value, "already_submitted": True}
    if document.get("ap_status") != InvoiceAPStatus.CODING.value:
        raise HTTPException(409, "The invoice is not ready to submit. Finish matching and resolve all exceptions first.")
    if document.get("gl_coding_status") not in {"auto_coded", "approved"}:
        raise HTTPException(409, "GL coding is not complete. Assign or review all line-item accounts first.")
    open_exceptions = database.table("invoice_exceptions").select("id").eq("org_id", str(ctx.org_id)).eq("document_id", str(document_id)).in_("status", ["open", "in_review", "escalated"]).execute().data or []
    if open_exceptions:
        raise HTTPException(409, "Resolve or formally waive all open AP exceptions before submitting for approval.")
    codings = database.table("invoice_codings").select("id,status,gl_account_id").eq("org_id", str(ctx.org_id)).eq("document_id", str(document_id)).execute().data or []
    if not codings or any(not row.get("gl_account_id") or row.get("status") not in {"auto_coded", "approved"} for row in codings):
        raise HTTPException(409, "Every invoice line must have a valid GL account before approval submission.")
    analyses = database.table("document_analyses").select("id").eq("org_id", str(ctx.org_id)).eq("document_id", str(document_id)).order("created_at", desc=True).limit(1).execute().data or []
    if not analyses:
        raise HTTPException(409, "Document analysis is required before approval submission.")
    try:
        await APApprovalBridge(database).create_workflow(org_id=ctx.org_id, document_id=document_id, analysis_id=UUID(analyses[0]["id"]), initiated_by=ctx.user_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    current = await InvoiceStateMachine(database).get_status(document_id)
    if current == InvoiceAPStatus.CODING:
        await InvoiceStateMachine(database).transition(document_id, ctx.org_id, InvoiceAPStatus.AWAITING_APPROVAL, actor_id=ctx.user_id, triggered_by="user", reason="User submitted completed AP workflow for approval")
    database.table("documents").update({"processing_step": "ap_awaiting_approval", "processing_message": "Invoice submitted to the approval workflow.", "processing_progress": 100}).eq("org_id", str(ctx.org_id)).eq("id", str(document_id)).execute()
    return {"submitted": True, "ap_status": (await InvoiceStateMachine(database).get_status(document_id)).value}


@router.get("/documents/{document_id}/status")
async def ap_status(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    row = (
        db()
        .table("documents")
        .select(
            "id,ap_enabled,ap_status,ap_match_mode,match_status,two_way_match_passed,three_way_match_passed,purchase_order_id,goods_receipt_id,gl_coding_status,erp_bill_id,payment_ready_at,processing_step,processing_message,processing_progress,error_message,updated_at"
        )
        .eq("org_id", str(ctx.org_id))
        .eq("id", str(document_id))
        .limit(1)
        .execute()
        .data
    )
    if not row:
        raise HTTPException(404, "Document not found")
    return row[0]

# ============================================================
# AP Dashboard
# ============================================================

from datetime import date
from app.services.fx.fx_service import FXRateUnavailable
from app.schemas.ap_dashboard import (
    APDashboardFilters,
    APSummaryResponse,
    APInvoiceListResponse,
    APTopVendorResponse,
    APAgingResponse,
)


def _dashboard_filters(
    date_from: date | None = None,
    date_to: date | None = None,
    vendor_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    currency: str | None = None,
    reporting_currency: str | None = None,
    search: str | None = None,
) -> APDashboardFilters:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be before or equal to date_to")
    if status and status not in {
        "received", "extracting", "validating", "matching", "coding",
        "awaiting_approval", "approved", "syncing_to_erp", "payment_ready",
        "paid", "reconciled", "match_exception", "coding_exception", "rejected",
        "on_hold", "overdue",
    }:
        raise HTTPException(status_code=422, detail="Unsupported AP invoice status")
    if priority and priority not in {"low", "medium", "high", "urgent"}:
        raise HTTPException(status_code=422, detail="Unsupported invoice priority")

    return APDashboardFilters(
        date_from=date_from,
        date_to=date_to,
        vendor_id=vendor_id,
        status=status,
        priority=priority,
        currency=currency.upper() if currency else None,
        reporting_currency=reporting_currency.upper() if reporting_currency else None,
        search=search,
    )


@router.get(
    "/dashboard/summary",
    response_model=APSummaryResponse,
    summary="AP dashboard summary",
)
async def ap_dashboard_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    vendor_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    currency: str | None = None,
    reporting_currency: str | None = None,
    search: str | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    filters = _dashboard_filters(
        date_from, date_to, vendor_id, status, priority, currency, reporting_currency, search
    )
    try:
        return await get_container().ap_dashboard_service.summary(ctx.org_id, filters)
    except FXRateUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/dashboard/invoices",
    response_model=APInvoiceListResponse,
    summary="List AP dashboard invoices",
)
async def ap_dashboard_invoices(
    date_from: date | None = None,
    date_to: date | None = None,
    vendor_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    currency: str | None = None,
    reporting_currency: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    filters = _dashboard_filters(
        date_from, date_to, vendor_id, status, priority, currency, reporting_currency, search
    )
    try:
        return await get_container().ap_dashboard_service.list_invoices(
            ctx.org_id,
            filters,
            limit,
            offset,
        )
    except FXRateUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/dashboard/top-vendors",
    response_model=list[APTopVendorResponse],
    summary="Top AP vendors by open balance",
)
async def ap_dashboard_top_vendors(
    date_from: date | None = None,
    date_to: date | None = None,
    vendor_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    currency: str | None = None,
    reporting_currency: str | None = None,
    search: str | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    filters = _dashboard_filters(
        date_from, date_to, vendor_id, status, priority, currency, reporting_currency, search
    )
    try:
        return await get_container().ap_dashboard_service.top_vendors(ctx.org_id, filters)
    except FXRateUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/dashboard/aging",
    response_model=APAgingResponse,
    summary="AP aging analysis",
)
async def ap_dashboard_aging(
    date_from: date | None = None,
    date_to: date | None = None,
    vendor_id: UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    currency: str | None = None,
    reporting_currency: str | None = None,
    search: str | None = None,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    filters = _dashboard_filters(
        date_from, date_to, vendor_id, status, priority, currency, reporting_currency, search
    )
    try:
        return await get_container().ap_dashboard_service.aging(ctx.org_id, filters)
    except FXRateUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
