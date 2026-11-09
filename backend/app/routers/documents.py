from __future__ import annotations

import logging
import asyncio
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user, require_verified_user
from app.core.authorization import require_permission
from app.core.config import settings
from app.core.container import get_container
from app.core.enum.database import DocumentType, DocumentStatus, RecommendationType
from app.core.limiter import limiter
from app.core.ocm import get_org_context
from app.core.permissions import (
    DELETE_DOCUMENTS,
    EDIT_DOCUMENTS,
    UPLOAD_DOCUMENTS,
    VIEW_DOCUMENTS,
)
from app.core.plan import batch_upload_limit_for
from app.core.supabase import get_supabase
from app.mappers.document_mapper import DocumentMapper
from app.repositories.document.document_repository import ap_owns_document_progress
from app.schemas.document import DocumentResponse, DocumentCaptureUpdate
from app.services.document.document_upload_service import (
    DuplicateDocumentError,
)
from app.services.document.document_capture_service import DocumentCaptureService, DocumentNotFoundError, DocumentCaptureConflictError

logger = logging.getLogger(__name__)


async def _run_ocr_background(document_id):
    try:
        await get_container().ocr_worker.execute(document_id=document_id)
    except Exception:
        logger.exception("Background OCR failed: document_id=%s", document_id)


def _schedule_ocr(document_id, mode: str = "intelligence") -> None:
    task = asyncio.create_task(
        get_container().ocr_worker.execute(document_id=document_id, mode=mode),
        name=f"ocr:{mode}:{document_id}",
    )
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    dependencies=[Depends(require_verified_user)],
)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def upload_document(
    response: Response,
    request: Request,
    file: UploadFile = File(...),
    industry: str = Form("general"),
    document_type: DocumentType = Form(DocumentType.UNKNOWN),
    currency: str = Form("USD"),
    financial_account_id: str | None = Form(None),
    allow_duplicate: bool = Form(False),
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(
        require_permission(UPLOAD_DOCUMENTS)
    ),
) -> DocumentResponse:
    if ctx.remaining_documents <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Monthly document limit reached. "
                "Please upgrade your plan."
            ),
        )

    allowed = set(settings.allowed_file_types)

    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: "
                f"{file.content_type}"
            ),
        )

    content = await file.read()

    max_bytes = (
        settings.max_file_size_mb * 1024 * 1024
    )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File exceeds the "
                f"{settings.max_file_size_mb}MB limit."
            ),
        )

    try:
        document = (
            await get_container()
            .document_upload_service
            .upload(
                org_id=ctx.org_id,
                user_id=user.id,
                filename=file.filename or "document",
                content_type=file.content_type,
                content=content,
                industry=industry,
                document_type=document_type,
                currency=currency,
                external_metadata=(
                    {
                        "financial_account_id":
                            financial_account_id
                    }
                    if financial_account_id
                    else {}
                ),
                allow_duplicate=allow_duplicate,
            )
        )

    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_DOCUMENT",
                "message": str(exc),
                "existing_document_id": (
                    str(exc.existing_document_id)
                    if exc.existing_document_id
                    else None
                ),
                "existing_file_name": exc.existing_file_name,
            },
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if document.status != DocumentStatus.QUARANTINED:
        _schedule_ocr(document.id, mode="intake")

    return DocumentMapper.to_response(
        document
    )


@router.post(
    "/batch",
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("5/minute")
async def upload_documents_batch(
    response: Response,
    request: Request,
    files: list[UploadFile] = File(...),
    industry: str = Form("general"),
    document_type: DocumentType = Form(DocumentType.UNKNOWN),
    currency: str = Form("USD"),
    allow_duplicate: bool = Form(False),
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(
        require_permission(UPLOAD_DOCUMENTS)
    ),
):
    batch_limit = batch_upload_limit_for(
        ctx.plan
    )

    if len(files) > batch_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Your {ctx.plan.value} plan allows "
                f"up to {batch_limit} files per upload. "
                f"You selected {len(files)}."
            ),
        )

    if ctx.remaining_documents < len(files):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"This batch needs {len(files)} documents "
                f"but only {ctx.remaining_documents} "
                f"remain on your monthly limit."
            ),
        )

    allowed = set(
        settings.allowed_file_types
    )

    max_bytes = (
        settings.max_file_size_mb * 1024 * 1024
    )

    results: list[dict] = []

    for file in files:
        try:
            if file.content_type not in allowed:
                results.append(
                    {
                        "filename": file.filename,
                        "status": "error",
                        "code": "UNSUPPORTED_FILE_TYPE",
                        "error": (
                            f"Unsupported file type: "
                            f"{file.content_type}"
                        ),
                    }
                )
                continue

            content = await file.read()

            if len(content) > max_bytes:
                results.append(
                    {
                        "filename": file.filename,
                        "status": "error",
                        "code": "FILE_TOO_LARGE",
                        "error": (
                            f"Exceeds the "
                            f"{settings.max_file_size_mb}MB "
                            f"limit."
                        ),
                    }
                )
                continue

            document = (
                await get_container()
                .document_upload_service
                .upload(
                    org_id=ctx.org_id,
                    user_id=user.id,
                    filename=file.filename or "document",
                    content_type=file.content_type,
                    content=content,
                    industry=industry,
                    document_type=document_type,
                    currency=currency,
                    allow_duplicate=allow_duplicate,
                )
            )

            if document.status != DocumentStatus.QUARANTINED:
                _schedule_ocr(document.id, mode="intake")

            response_document = (
                DocumentMapper
                .to_response(document)
                .model_dump(mode="json")
            )

            results.append(
                {
                    "filename": file.filename,
                    "status": "accepted",
                    "document": response_document,
                    "document_id": str(document.id),
                }
            )

        except DuplicateDocumentError as exc:
            results.append(
                {
                    "filename": file.filename,
                    "status": "error",
                    "code": "DUPLICATE_DOCUMENT",
                    "error": str(exc),
                    "existing_document_id": (
                        str(exc.existing_document_id)
                        if exc.existing_document_id
                        else None
                    ),
                    "existing_file_name": exc.existing_file_name,
                }
            )

        except ValueError as exc:
            results.append(
                {
                    "filename": file.filename,
                    "status": "error",
                    "code": "VALIDATION_ERROR",
                    "error": str(exc),
                }
            )

        except Exception:
            logger.exception(
                "Batch upload failed for file %s",
                file.filename,
            )

            results.append(
                {
                    "filename": file.filename,
                    "status": "error",
                    "code": "UPLOAD_FAILED",
                    "error": (
                        "Upload failed. "
                        "Please try this file again."
                    ),
                }
            )

    accepted = sum(
        1
        for item in results
        if item["status"] == "accepted"
    )

    return {
        "total": len(files),
        "accepted": accepted,
        "failed": len(files) - accepted,
        "results": results,
    }


@router.get("")
@limiter.limit("60/minute")
async def list_documents(
    response: Response,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    industry: str | None = None,
    query: str | None = None,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(
        require_permission(VIEW_DOCUMENTS)
    ),
) -> list[DocumentResponse]:
    limit = min(
        max(limit, 1),
        100,
    )
    if query and any(character in query for character in ",()"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Search cannot contain commas or parentheses.",
        )

    total_query = (
        get_supabase().table("documents")
        .select("id", count="exact", head=True)
        .eq("org_id", str(ctx.org_id))
        .eq("is_archived", False)
    )
    if industry:
        total_query = total_query.eq("industry", industry)
    if query and (term := query.strip()):
        total_query = total_query.or_(
            f"document_number.ilike.*{term}*,vendor_name.ilike.*{term}*"
        )
    total_result = total_query.execute()
    response.headers["X-Total-Count"] = str(total_result.count or 0)

    documents = (
        await get_container()
        .document_service
        .list_documents(
            ctx.org_id,
            limit=limit,
            offset=offset,
            industry=industry,
            query=query,
        )
    )

    responses = [DocumentMapper.to_response(item) for item in documents]
    if not responses:
        return responses

    ids = [str(item.id) for item in responses]
    database = get_supabase()
    line_rows = database.table("document_line_items").select("document_id,quantity").eq("org_id", str(ctx.org_id)).in_("document_id", ids).execute().data or []
    coding_rows = database.table("invoice_codings").select("document_id,gl_account_id,line_item_id").eq("org_id", str(ctx.org_id)).in_("document_id", ids).execute().data or []
    capture_rows = database.table("documents").select("id,classification_confidence,classification_reason,classified_at,human_review_status,intelligence_status,capture_status,capture_progress,capture_error,capture_overrides").eq("org_id", str(ctx.org_id)).in_("id", ids).execute().data or []
    line_by_doc = {}
    for row in line_rows:
        line_by_doc.setdefault(str(row["document_id"]), []).append(row)
    coding_by_doc = {}
    for row in coding_rows:
        key = str(row["document_id"])
        if key not in coding_by_doc or row.get("line_item_id") is None:
            coding_by_doc[key] = row
    capture_by_doc = {str(row["id"]): row for row in capture_rows}
    enriched = []
    for item in responses:
        key = str(item.id)
        lines = line_by_doc.get(key, [])
        coding = coding_by_doc.get(key) or {}
        capture = capture_by_doc.get(key) or {}
        total_qty = sum((float(row.get("quantity") or 0) for row in lines), 0.0)
        payload = item.model_dump(mode="json")
        overrides = capture.get("capture_overrides") or {}
        account = overrides.get("account") if isinstance(overrides, dict) else {}
        if not isinstance(account, dict):
            account = {}
        account_id = account.get("id") or coding.get("gl_account_id")
        account_code = account.get("code")
        account_name = account.get("name")
        if account_id and (not account_code or not account_name):
            account_rows = database.table("chart_of_accounts").select("id,account_code,account_name").eq("org_id", str(ctx.org_id)).eq("id", str(account_id)).limit(1).execute().data or []
            if account_rows:
                account_code = account_code or account_rows[0].get("account_code")
                account_name = account_name or account_rows[0].get("account_name")
        payload.update({
            "total_quantity": total_qty,
            "line_item_count": len(lines),
            "account_id": account_id,
            "account_code": account_code,
            "account_name": account_name,
        })
        for field in ("classification_confidence","classification_reason","classified_at","human_review_status","intelligence_status","capture_status","capture_progress","capture_error"):
            payload[field] = capture.get(field)
        payload["capture_overrides"] = capture.get("capture_overrides") or {}
        enriched.append(DocumentResponse.model_validate(payload))
    return enriched


@router.get("/{document_id}/workflow")
@limiter.limit("60/minute")
async def get_document_workflow(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    try:
        did = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document id",
        ) from exc

    row = (
        get_supabase()
        .table("documents")
        .select(
            "id,"
            "document_type,"
            "classification_confidence,"
            "classification_reason,"
            "workflow_route,"
            "classified_at,"
            "status,"
            "pipeline_stage,"
            "ap_status,"
            "match_status,"
            "gl_coding_status,"
            "error_message"
        )
        .eq("id", str(did))
        .eq("org_id", str(ctx.org_id))
        .single()
        .execute()
        .data
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return row


@router.get("/{document_id}/intelligence")
@limiter.limit("120/minute")
async def get_document_intelligence(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
):
    """Return the complete UI-ready document intelligence payload."""
    try:
        did = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document id") from exc

    database = get_supabase()

    # This endpoint is polled while OCR runs. Keep the hot path to one
    # document query; load OCR/analysis/vendor data only after processing is terminal.
    def _read_processing_row() -> list[dict]:
        return (
            database.table("documents")
            .select(
                "id,org_id,document_type,industry,file_name,status,pipeline_stage,workflow_route,"
                "processing_step,processing_message,processing_progress,error_message,validation_warnings,"
                "human_review_status,intelligence_status,capture_status,capture_progress,capture_error,capture_overrides,created_at,updated_at,"
                "vendor_name,document_number,document_date,due_date,currency,payment_terms,payment_method,"
                "subtotal,tax_amount,total_amount,amount_paid,amount_due"
            )
            .eq("id", str(did)).eq("org_id", str(ctx.org_id)).limit(1).execute().data or []
        )

    # Supabase's Python client is synchronous. Never let a polling request
    # block FastAPI's event loop while the database call is in flight; that
    # can delay the OCR background task that was just scheduled after upload.
    rows = await asyncio.to_thread(_read_processing_row)
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = rows[0]
    step = str(doc.get("processing_step") or "").lower()
    status_value = str(doc.get("status") or "").lower()
    intelligence_status = str(doc.get("intelligence_status") or "not_requested").lower()
    terminal = intelligence_status in {"not_requested", "complete", "failed"} or step == "ap_ready"

    if not terminal:
        return {
            "document": doc, "ocr": None, "analysis": None, "embedding": None,
            "line_items": [], "vendor": None, "vendor_embedding_ready": False,
            "structured_data": {
                "industry": doc.get("industry") or "general",
                "document_type": doc.get("document_type"),
                "sections": {"document": {
                    "file_name": doc.get("file_name"), "document_type": doc.get("document_type"),
                    "vendor_name": doc.get("vendor_name"), "document_number": doc.get("document_number"),
                    "document_date": doc.get("document_date"), "due_date": doc.get("due_date"),
                    "currency": doc.get("currency"), "payment_terms": doc.get("payment_terms"),
                    "payment_method": doc.get("payment_method"),
                }},
                "ocr_captured_fields": {}, "line_items": [],
                "raw_totals": {k: doc.get(k) for k in ("subtotal","tax_amount","discount_amount","total_amount","amount_paid","amount_due")},
                "extraction_confidence": "low",
            },
            "ready": False,
            "actions": [],
        }

    # Terminal requests are infrequent. Refresh the complete document only now.
    full_rows = (
        database.table("documents")
        .select(
            "id,org_id,document_type,industry,file_name,file_url,file_type,status,pipeline_stage,"
            "workflow_route,processing_step,processing_message,processing_progress,"
            "error_message,validation_warnings,human_review_status,intelligence_status,capture_status,capture_progress,capture_error,capture_overrides,vendor_id,vendor_name,document_number,"
            "document_date,due_date,subtotal,tax_amount,tax_rate,discount_amount,"
            "total_amount,amount_paid,amount_due,currency,payment_terms,payment_method,purchase_order_id,"
            "ap_status,ap_enabled,sheets_url,created_at,updated_at"
        )
        .eq("id", str(did)).eq("org_id", str(ctx.org_id)).limit(1).execute().data or []
    )
    if full_rows:
        doc = full_rows[0]

    ocr_rows = (
        database.table("ocr_results").select(
            "id,raw_text,page_count,pages,tables_detected,key_value_pairs,language_detected,"
            "is_handwritten,is_scanned,has_tables,has_signatures,image_quality,engine,engine_version,"
            "confidence_score,processing_ms,tokens_used,created_at"
        ).eq("document_id", str(did)).eq("org_id", str(ctx.org_id))
        .order("created_at", desc=True).limit(1).execute().data or []
    )
    ocr = ocr_rows[0] if ocr_rows else None
    if ocr:
        raw_text = str(ocr.get("raw_text") or "").strip()
        if not raw_text:
            pages = ocr.get("pages") or []
            if isinstance(pages, list):
                page_texts = [
                    str(page.get("text") or "").strip()
                    for page in pages
                    if isinstance(page, dict) and page.get("text")
                ]
                if page_texts:
                    ocr["raw_text"] = "\n\n".join(page_texts)
    analysis_rows = (
        database.table("document_analyses").select("*")
        .eq("document_id", str(did)).eq("org_id", str(ctx.org_id))
        .order("created_at", desc=True).limit(1).execute().data or []
    )
    analysis = analysis_rows[0] if analysis_rows else None
    line_items = (
        database.table("document_line_items").select("*")
        .eq("document_id", str(did)).eq("org_id", str(ctx.org_id))
        .order("position").execute().data or []
    )
    embedding_rows = (
        database.table("document_embeddings").select("id,model_used,created_at")
        .eq("document_id", str(did)).limit(1).execute().data or []
    )
    vendor = None
    vendor_embedding_ready = False
    if doc.get("vendor_id"):
        vendor_rows = (
            database.table("vendors").select(
                "id,name,risk_score,risk_level,is_verified,is_blocked,total_spend,average_spend,"
                "invoice_count,fraud_flags,anomaly_count,ai_summary,ai_risk_explanation"
            ).eq("id", str(doc["vendor_id"])).eq("org_id", str(ctx.org_id))
            .limit(1).execute().data or []
        )
        vendor = vendor_rows[0] if vendor_rows else None
        vendor_embedding_ready = bool(
            database.table("vendor_embeddings").select("id")
            .eq("vendor_id", str(doc["vendor_id"])).limit(1).execute().data or []
        )
    confidence = float((ocr or {}).get("confidence_score") or 0)
    kv = (ocr or {}).get("key_value_pairs") or {}
    structured_data = {
        "industry": doc.get("industry") or "general", "document_type": doc.get("document_type"),
        "sections": {"document": {
            "file_name": doc.get("file_name"), "document_type": doc.get("document_type"),
            "vendor_name": doc.get("vendor_name"), "document_number": doc.get("document_number"),
            "document_date": doc.get("document_date"), "due_date": doc.get("due_date"),
            "currency": doc.get("currency"), "payment_terms": doc.get("payment_terms"),
            "payment_method": doc.get("payment_method"),
        }, "ocr_captured_fields": kv, "line_items": line_items},
        "raw_totals": {k: doc.get(k) for k in ("subtotal","tax_amount","discount_amount","total_amount","amount_paid","amount_due")},
        "extraction_confidence": "high" if confidence >= .85 else "medium" if confidence >= .60 else "low",
    }
    ready = step == "complete" and status_value != "failed" and bool(analysis)
    if doc.get("error_message") and not analysis:
        ready = False
    source_document = None
    source_path = str(doc.get("file_url") or "").strip()
    if source_path:
        try:
            signed_url = await get_container().storage_service.create_signed_url(
                path=source_path,
                expires_in=3600,
            )
            source_document = {
                "url": signed_url,
                "file_name": doc.get("file_name"),
                "file_type": doc.get("file_type"),
                "expires_in": 3600,
            }
        except Exception:
            logger.exception(
                "Could not create source document preview URL: document_id=%s",
                did,
            )

    capture_ready = str(doc.get("capture_status") or "pending") == "complete"
    actions = ["download", "export"] if ready else []
    if capture_ready and not analysis:
        actions.append("run_ai_analysis")
        if doc.get("document_type") == "invoice":
            actions.append("run_ap")
    if ready and doc.get("document_type") == "invoice" and "run_ap" not in actions:
        actions.append("run_ap")
    if doc.get("workflow_route"):
        actions.append("workflow_review")
    return {
        "document": doc,
        "ocr": ocr,
        "analysis": analysis,
        "embedding": embedding_rows[0] if embedding_rows else None,
        "line_items": line_items,
        "structured_data": structured_data,
        "vendor": vendor,
        "vendor_embedding_ready": vendor_embedding_ready,
        "source_document": source_document,
        "ready": ready,
        "actions": actions,
    }


@router.get("/{document_id}/capture-options")
@limiter.limit("120/minute")
async def document_capture_options(
    response: Response,
    request: Request,
    document_id: UUID,
    field: str,
    q: str = "",
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
):
    try:
        options = DocumentCaptureService().options(org_id=ctx.org_id, document_id=document_id, field=field, query=q)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"field": field, "options": options}


@router.patch("/{document_id}/capture")
@limiter.limit("60/minute")
async def update_document_capture(
    response: Response,
    request: Request,
    document_id: UUID,
    payload: DocumentCaptureUpdate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(EDIT_DOCUMENTS)),
):
    try:
        return await DocumentCaptureService().update_capture(
            org_id=ctx.org_id,
            user_id=user.id,
            document_id=document_id,
            payload=payload.model_dump(exclude_none=True, mode="python"),
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DocumentCaptureConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{document_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def analyze_document(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(UPLOAD_DOCUMENTS)),
):
    """Explicitly start Document Intelligence for an accepted upload.

    Uploading a file only stores it. This endpoint is the sole entry point
    for the full OCR/extraction/classification/AI-analysis pipeline.
    """
    try:
        did = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document id") from exc

    database = get_supabase()
    rows = (
        database.table("documents")
        .select("id,status,human_review_status,intelligence_status,processing_step,is_archived,ap_enabled,ap_status")
        .eq("id", str(did)).eq("org_id", str(ctx.org_id)).limit(1).execute().data or []
    )
    if not rows or rows[0].get("is_archived"):
        raise HTTPException(status_code=404, detail="Document not found")

    document = rows[0]
    if ap_owns_document_progress(
        ap_enabled=document.get("ap_enabled"),
        ap_status=document.get("ap_status"),
    ):
        raise HTTPException(
            status_code=409,
            detail="This invoice is managed by Accounts Payable. Resume or resolve the AP workflow instead of starting Document Intelligence.",
        )

    if document.get("intelligence_status") in {"queued", "processing"}:
        return {"queued": False, "document_id": str(did), "intelligence_status": document.get("intelligence_status")}

    database.table("documents").update({
        "intelligence_status": "queued",
        "processing_step": "queued",
        "processing_message": "Document Intelligence is queued",
        "processing_progress": 0,
        "error_message": None,
    }).eq("id", str(did)).eq("org_id", str(ctx.org_id)).execute()

    _schedule_ocr(did)
    return {"queued": True, "document_id": str(did), "intelligence_status": "queued"}


@router.post("/{document_id}/review")
@limiter.limit("30/minute")
async def review_document(
    document_id,
    request: Request,
    response: Response,
    decision: RecommendationType,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
):
    try:
        did = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document id") from exc

    database = get_supabase()
    if not (database.table("documents").select("id").eq("id", str(did)).eq("org_id", str(ctx.org_id)).limit(1).execute().data or []):
        raise HTTPException(status_code=404, detail="Document not found")

    analyses = (
        database.table("document_analyses").select("id")
        .eq("document_id", str(did)).eq("org_id", str(ctx.org_id))
        .order("created_at", desc=True).limit(1).execute().data or []
    )

    # Human intake acceptance is deliberately independent from Document
    # Intelligence. An upload can be accepted before any AI analysis exists.
    if decision == RecommendationType.REJECT:
        database.table("documents").update({"human_review_status": "declined"}).eq("id", str(did)).eq("org_id", str(ctx.org_id)).execute()
        if analyses:
            await get_container().analysis_repository.submit_review(
                analysis_id=str(analyses[0]["id"]), reviewer_id=str(user.id), decision=decision,
            )
        await get_container().document_service.archive_document(
            did,
            user.id,
            reason="human_review_declined",
        )
        return {
            "ok": True,
            "document_id": str(did),
            "decision": decision.value,
            "deleted": True,
        }

    # If an AI analysis exists, preserve its audit/review record as well.
    if analyses:
        await get_container().analysis_repository.submit_review(
            analysis_id=str(analyses[0]["id"]), reviewer_id=str(user.id), decision=decision,
        )

    database.table("documents").update({
        "human_review_status": "accepted",
    }).eq("id", str(did)).eq("org_id", str(ctx.org_id)).execute()
    if not analyses:
        await get_container().document_repository.update_document_status(did, DocumentStatus.APPROVED)
    return {
        "ok": True,
        "document_id": str(did),
        "decision": decision.value,
        "deleted": False,
    }



@router.post(
    "/{document_id}/retry-processing",
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def retry_failed_document_processing(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(UPLOAD_DOCUMENTS)),
):
    """Retry one failed document explicitly, without a UI retry loop."""
    try:
        did = UUID(str(document_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document id",
        ) from exc

    database = get_supabase()

    # Scope the lookup to the user's organization.
    try:
        rows = (
            await asyncio.to_thread(
                lambda: (
                    database.table("documents")
                    .select(
                        "id,status,capture_status,"
                        "intelligence_status,pipeline_stage,ap_enabled,ap_status"
                    )
                    .eq("id", str(did))
                    .eq("org_id", str(ctx.org_id))
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
            )
        )
    except Exception as exc:
        logger.exception(
            "Could not load document for retry: document_id=%s",
            did,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not check document status. Please try again.",
        ) from exc

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    row = rows[0]

    if ap_owns_document_progress(
        ap_enabled=row.get("ap_enabled"),
        ap_status=row.get("ap_status"),
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This invoice is managed by Accounts Payable. Resume or resolve the AP workflow instead of retrying Document Intelligence.",
        )

    failed = any(
        str(row.get(field) or "").strip().lower() == "failed"
        for field in (
            "status",
            "capture_status",
            "intelligence_status",
            "pipeline_stage",
        )
    )

    if not failed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed documents can be retried.",
        )

    # Retry telemetry should not prevent recovery of the document.
    # If the counter RPC fails, log it and continue, but do not claim
    # that the retry counter was incremented successfully.
    try:
        await get_container().document_service.repository.increment_retry(did)
    except Exception:
        logger.exception(
            "Retry counter increment failed; continuing with document retry: "
            "document_id=%s",
            did,
        )

    # Clear the previous failure before scheduling the worker.
    try:
        update_result = await asyncio.to_thread(
            lambda: (
                database.table("documents")
                .update({
                    "status": DocumentStatus.PENDING.value,
                    "pipeline_stage": "intake",
                    "capture_status": "pending",
                    "capture_progress": 0,
                    "capture_error": None,
                    "intelligence_status": "not_requested",
                    "processing_step": "intake",
                    "processing_message": "Retry requested",
                    "processing_progress": 0,
                    "error_message": None,
                })
                .eq("id", str(did))
                .eq("org_id", str(ctx.org_id))
                .execute()
            )
        )
    except Exception as exc:
        logger.exception(
            "Could not reset document state for retry: document_id=%s",
            did,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not prepare this document for retry.",
        ) from exc

    # Supabase update responses normally contain the updated rows.
    # If the API returned no updated row, do not report a successful retry.
    if not getattr(update_result, "data", None):
        logger.error(
            "Document retry update affected no rows: document_id=%s org_id=%s",
            did,
            ctx.org_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The document could not be updated for retry. Refresh and try again.",
        )

    # Schedule only after the state reset has succeeded.
    try:
        _schedule_ocr(did, mode="intake")
    except Exception as exc:
        logger.exception(
            "Could not schedule OCR retry: document_id=%s",
            did,
        )

        # Restore a visible failure state if task creation itself fails.
        try:
            await asyncio.to_thread(
                lambda: (
                    database.table("documents")
                    .update({
                        "status": DocumentStatus.FAILED.value,
                        "pipeline_stage": "failed",
                        "capture_status": "failed",
                        "capture_error": "Could not start document processing. Please retry.",
                        "processing_step": "failed",
                        "processing_message": "Could not start document processing",
                        "error_message": "Could not schedule OCR retry",
                    })
                    .eq("id", str(did))
                    .eq("org_id", str(ctx.org_id))
                    .execute()
                )
            )
        except Exception:
            logger.exception(
                "Could not restore failed state after scheduling error: "
                "document_id=%s",
                did,
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not start document processing. Please try again.",
        ) from exc

    logger.info(
        "Document retry scheduled: document_id=%s org_id=%s user_id=%s",
        did,
        ctx.org_id,
        user.id,
    )

    return {
        "ok": True,
        "document_id": str(did),
        "status": "queued",
        "message": "Document retry started.",
    }



@router.post("/{document_id}/ocr", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def rerun_document_ocr(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(UPLOAD_DOCUMENTS)),
):
    """Backward-compatible alias for explicitly running Document Intelligence."""
    try:
        did = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document id") from exc

    document = await get_container().document_service.get_document(did)
    if document is None or document.org_id != ctx.org_id or getattr(document, "is_archived", False):
        raise HTTPException(status_code=404, detail="Document not found")

    row = get_supabase().table("documents").select("human_review_status,ap_enabled,ap_status").eq("id", str(did)).eq("org_id", str(ctx.org_id)).limit(1).execute().data or []
    if not row or row[0].get("human_review_status") != "accepted":
        raise HTTPException(status_code=409, detail="Accept the document before running Document Intelligence.")
    if ap_owns_document_progress(
        ap_enabled=row[0].get("ap_enabled"),
        ap_status=row[0].get("ap_status"),
    ):
        raise HTTPException(
            status_code=409,
            detail="This invoice is managed by Accounts Payable. Resume or resolve the AP workflow instead of starting Document Intelligence.",
        )
    get_supabase().table("documents").update({
        "intelligence_status": "queued",
        "processing_step": "queued",
        "processing_message": "Document Intelligence is queued",
        "processing_progress": 0,
        "error_message": None,
    }).eq("id", str(did)).eq("org_id", str(ctx.org_id)).execute()
    _schedule_ocr(did)
    return {"ok": True, "document_id": str(did), "status": "queued"}


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
@limiter.limit("60/minute")
async def get_document(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(
        require_permission(VIEW_DOCUMENTS)
    ),
) -> DocumentResponse:
    try:
        document_uuid = UUID(
            str(document_id)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document id",
        ) from exc

    document = (
        await get_container()
        .document_service
        .get_document(document_uuid)
    )

    if document.org_id != ctx.org_id:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return DocumentMapper.to_response(
        document
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("30/minute")
async def delete_document(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(
        require_permission(DELETE_DOCUMENTS)
    ),
) -> None:
    try:
        document_uuid = UUID(
            str(document_id)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document id",
        ) from exc

    document = (
        await get_container()
        .document_service
        .get_document(document_uuid)
    )

    if document.org_id != ctx.org_id:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    await (
        get_container()
        .document_service
        .archive_document(
            document_uuid,
            user.id,
            reason="user_requested_delete",
        )
    )
