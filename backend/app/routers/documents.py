from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
    Request,
    Response,
)

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.ocm import get_org_context
from app.core.container import get_container
from app.core.limiter import limiter
from app.core.supabase import get_supabase
from app.core.authorization import require_permission
from app.core.permissions import VIEW_DOCUMENTS, UPLOAD_DOCUMENTS, DELETE_DOCUMENTS
from app.core.enum.database import DocumentType
from app.core.plan import batch_upload_limit_for
from app.mappers.document_mapper import DocumentMapper
from app.schemas.document import DocumentResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def upload_document(
    response: Response,
    request: Request,
    file: UploadFile = File(...),
    industry: str = Form("general"),
    document_type: DocumentType = Form(DocumentType.UNKNOWN),
    currency: str = Form("USD"),
    financial_account_id: str | None = Form(None),
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(UPLOAD_DOCUMENTS)),
) -> DocumentResponse:
    """Create a V2 document intake record.

    The endpoint stores the original file and creates a PENDING document.
    OCR and analysis are performed asynchronously by the V2 worker pipeline.
    """

    if ctx.remaining_documents <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Document processing limit reached for this organization.",
        )

    allowed = set(settings.allowed_file_types)
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    content = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_file_size_mb}MB limit.",
        )

    try:
        document = await get_container().document_upload_service.upload(
            org_id=ctx.org_id,
            user_id=user.id,
            filename=file.filename or "document",
            content_type=file.content_type,
            content=content,
            industry=industry,
            document_type=document_type,
            currency=currency,
            external_metadata=(
                {"financial_account_id": financial_account_id}
                if financial_account_id
                else {}
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return DocumentMapper.to_response(document)


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
async def upload_documents_batch(
    response: Response,
    request: Request,
    files: list[UploadFile] = File(...),
    industry: str = Form("general"),
    document_type: DocumentType = Form(DocumentType.UNKNOWN),
    currency: str = Form("USD"),
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(UPLOAD_DOCUMENTS)),
):
    """
    Upload several documents in one request — see
    core/plan.py's max_batch_upload for why this is capped per plan
    (not a value-gate, a burst-size ceiling so one request can't dump
    a whole month's quota or hundreds of files on the OCR queue at
    once).

    Partial success by design: one bad file in the batch does not
    fail the whole request. Each file gets its own result with either
    a created document or an error, same shape either way, so the
    frontend can render a per-file status list.
    """
    batch_limit = batch_upload_limit_for(ctx.plan)
    if len(files) > batch_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Your {ctx.plan.value} plan allows up to {batch_limit} files per upload. "
                   f"You selected {len(files)}. Upload in smaller batches, or upgrade for a higher limit.",
        )

    if ctx.remaining_documents < len(files):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"This batch needs {len(files)} documents but only {ctx.remaining_documents} "
                   f"remain on your monthly limit.",
        )

    allowed = set(settings.allowed_file_types)
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    results = []
    for f in files:
        try:
            if f.content_type not in allowed:
                results.append({"filename": f.filename, "status": "error", "error": f"Unsupported file type: {f.content_type}"})
                continue

            content = await f.read()
            if len(content) > max_bytes:
                results.append({"filename": f.filename, "status": "error", "error": f"Exceeds the {settings.max_file_size_mb}MB limit."})
                continue

            document = await get_container().document_upload_service.upload(
                org_id=ctx.org_id,
                user_id=user.id,
                filename=f.filename or "document",
                content_type=f.content_type,
                content=content,
                industry=industry,
                document_type=document_type,
                currency=currency,
            )
            results.append({"filename": f.filename, "status": "accepted", "document": DocumentMapper.to_response(document).model_dump(mode="json")})

        except ValueError as exc:
            results.append({"filename": f.filename, "status": "error", "error": str(exc)})
        except Exception:
            # One file's unexpected failure should never take the whole
            # batch down with it — log it, report it, keep processing
            # the rest.
            import logging
            logging.getLogger(__name__).exception("Batch upload failed for file %s", f.filename)
            results.append({"filename": f.filename, "status": "error", "error": "Upload failed. Please try this file again."})

    accepted = sum(1 for r in results if r["status"] == "accepted")
    return {
        "total": len(files),
        "accepted": accepted,
        "failed": len(files) - accepted,
        "results": results,
    }


@router.get("", response_model=list[DocumentResponse])
@limiter.limit("60/minute")
async def list_documents(
    response: Response,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
) -> list[DocumentResponse]:
    limit = min(max(limit, 1), 100)
    documents = await get_container().document_service.list_documents(
        ctx.org_id, limit=limit, offset=offset
    )
    return [DocumentMapper.to_response(item) for item in documents]


@router.get("/{document_id}/workflow")
@limiter.limit("60/minute")
async def get_document_workflow(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    from uuid import UUID

    try:
        did = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document id") from exc
    row = (
        get_supabase()
        .table("documents")
        .select(
            "id,document_type,classification_confidence,classification_reason,workflow_route,classified_at,status,pipeline_stage,ap_status,match_status,gl_coding_status"
        )
        .eq("id", str(did))
        .eq("org_id", str(ctx.org_id))
        .single()
        .execute()
        .data
    )
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return row


@router.get("/{document_id}", response_model=DocumentResponse)
@limiter.limit("60/minute")
async def get_document(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
) -> DocumentResponse:
    from uuid import UUID

    try:
        document_uuid = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document id") from exc
    document = await get_container().document_service.get_document(document_uuid)
    if document.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentMapper.to_response(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_document(
    response: Response,
    request: Request,
    document_id,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(DELETE_DOCUMENTS)),
) -> None:
    from uuid import UUID

    try:
        document_uuid = UUID(str(document_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document id") from exc
    document = await get_container().document_service.get_document(document_uuid)
    if document.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    # Archive is the V2-safe deletion semantic; physical storage cleanup is
    # handled by the document lifecycle rather than the HTTP layer.
    await get_container().document_service.archive_document(
        document_uuid, user.id, reason="user_requested_delete"
    )
