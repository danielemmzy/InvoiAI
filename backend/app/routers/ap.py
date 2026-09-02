from __future__ import annotations
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from app.context import OrganizationContext
from app.core.ocm import get_org_context
from app.core.permissions import VIEW_FINANCE, MANAGE_FINANCE
from app.core.authorization import require_permission
from app.core.limiter import limiter
from app.core.redis import get_redis
from app.core.supabase import get_supabase
from app.services.ap.exception_service import ExceptionService
from app.services.ap.approval_bridge import APApprovalBridge
from app.services.ap.chart_of_accounts_service import ChartOfAccountsService
from app.core.enum.database import IntegrationProvider
from app.repositories.integration.integration_repository import (
    IntegrationConnectionRepository,
)

router = APIRouter(prefix="/ap", tags=["AP Automation"])


def db():
    return get_supabase()


@router.get("/exceptions")
async def list_exceptions(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    rows = await ExceptionService().list_open(ctx.org_id)
    return [r.model_dump(mode="json") for r in rows]


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
    result = await ExceptionService().resolve(
        ctx.org_id, exception_id, ctx.user_id, body.get("note", "") or "", False
    )
    return {"resolved": bool(result.data)}


@router.post("/exceptions/{exception_id}/waive")
async def waive_exception(
    exception_id: UUID,
    body: dict,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    result = await ExceptionService().resolve(
        ctx.org_id, exception_id, ctx.user_id, body.get("note", "") or "", True
    )
    return {"waived": bool(result.data)}


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
        .select("id,status")
        .eq("org_id", str(ctx.org_id))
        .eq("document_id", str(document_id))
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(404, "No codings found")
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
    if not analysis:
        raise HTTPException(409, "Analysis not found for document")
    await APApprovalBridge().create_workflow(
        org_id=ctx.org_id,
        document_id=document_id,
        analysis_id=UUID(analysis[0]["id"]),
        initiated_by=ctx.user_id,
    )
    return {"approved": True, "routed_to_approval": True}


@router.get("/chart-of-accounts")
async def chart_of_accounts(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_FINANCE)),
):
    return await ChartOfAccountsService().list(ctx.org_id)


@router.post("/chart-of-accounts/sync")
@limiter.limit("5/minute")
async def sync_chart_of_accounts(
    request: Request,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    """Import the organization's QuickBooks Chart of Accounts into InvoiAI."""
    redis = await get_redis()
    lock = redis.lock(f"invoiai:coa:sync:{ctx.org_id}", timeout=600, blocking=False)
    if not await lock.acquire():
        raise HTTPException(
            status_code=409, detail="Chart of Accounts sync is already running."
        )
    try:
        connection = await IntegrationConnectionRepository().get_org_connection(
            ctx.org_id,
            IntegrationProvider.QUICKBOOKS,
        )
        if not connection or not connection.is_active or not connection.realm_id:
            raise HTTPException(
                status_code=409,
                detail="Connect an active QuickBooks accounting connection first.",
            )

        try:
            result = await ChartOfAccountsService().sync_from_quickbooks(
                ctx.org_id,
                connection.realm_id,
            )
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "QuickBooks Chart of Accounts sync failed", exc_info=exc
            )
            raise HTTPException(
                status_code=502,
                detail="QuickBooks Chart of Accounts sync failed. Please retry shortly.",
            ) from exc

        return {
            "provider": "quickbooks",
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
    body: dict,
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(MANAGE_FINANCE)),
):
    payload = {
        "org_id": str(ctx.org_id),
        "account_code": body.get("account_code"),
        "account_name": body.get("account_name"),
        "account_type": body.get("account_type", "expense"),
        "account_subtype": body.get("account_subtype"),
        "external_id": body.get("external_id"),
        "is_active": body.get("is_active", True),
        "is_postable": body.get("is_postable", True),
        "source": body.get("source", "manual"),
    }
    if not payload["account_code"] or not payload["account_name"]:
        raise HTTPException(400, "account_code and account_name are required")
    result = db().table("chart_of_accounts").insert(payload).execute().data[0]
    await ChartOfAccountsService().invalidate(ctx.org_id)
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
    org = (
        db()
        .table("organizations")
        .select("slug")
        .eq("id", str(ctx.org_id))
        .single()
        .execute()
        .data
    )
    local = f"invoices+{org['slug']}".lower().replace(" ", "-")
    domain = __import__(
        "app.core.config", fromlist=["settings"]
    ).settings.ap_email_inbound_domain
    address = f"{local}@{domain}"
    existing = (
        db()
        .table("ap_email_intake_addresses")
        .select("*")
        .eq("org_id", str(ctx.org_id))
        .eq("is_active", True)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return existing[0]
    return (
        db()
        .table("ap_email_intake_addresses")
        .insert(
            {
                "org_id": str(ctx.org_id),
                "email_address": address,
                "created_by": str(ctx.user_id),
            }
        )
        .execute()
        .data[0]
    )


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
            "id,ap_status,match_status,gl_coding_status,erp_bill_id,payment_ready_at"
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
