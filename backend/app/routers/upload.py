import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from app.core.config import settings
from app.core.limiter import limiter
from app.core.auth import get_current_user, AuthUser
from app.core.supabase import get_supabase
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.gpt_extractor import extract_from_text, extract_from_image
from app.services.validator import validate_document
from app.services.usage import check_usage_limit, increment_usage
from app.models.invoice import UploadResponse, SUPPORTED_INDUSTRIES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("", response_model=UploadResponse)
@limiter.limit("10/minute")
@limiter.limit("100/day")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    industry: str = Form(default="general"),
    current_user: AuthUser = Depends(get_current_user),  # REAL AUTH
):
    """
    Processes a document for the authenticated user.

    Requires: Authorization: Bearer <access_token> header
    Form fields: file (PDF/image), industry (from supported list)

    Pipeline:
    1. Validate JWT → get real user
    2. Check monthly usage limit for their plan
    3. Validate file
    4. Extract text or use Vision
    5. Validate extracted data
    6. Save to storage + DB
    7. Increment usage count
    8. Return structured result
    """

    # ── Usage limit check (before any processing) ─────────────────────────────
    # Checked first so we don't waste OpenAI credits on users over their limit
    await check_usage_limit(current_user.id, current_user.plan)

    # ── File validation ───────────────────────────────────────────────────────
    if file.content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not supported. Accepted: PDF, JPEG, PNG, WEBP"
        )

    if industry not in SUPPORTED_INDUSTRIES:
        raise HTTPException(
            status_code=400,
            detail=f"Industry '{industry}' not supported. Call GET /industries for the list."
        )

    file_bytes = await file.read()

    if len(file_bytes) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum is {settings.max_file_size_mb}MB."
        )

    invoice_id = str(uuid.uuid4())
    mime_type = file.content_type
    raw_text = ""

    logger.info(
        f"[{invoice_id}] user={current_user.id} "
        f"file={file.filename} industry={industry} plan={current_user.plan}"
    )

    # ── Extraction ────────────────────────────────────────────────────────────
    try:
        if mime_type == "application/pdf":
            raw_text, is_digital = extract_text_from_pdf(file_bytes)
            if is_digital:
                logger.info(f"[{invoice_id}] Digital PDF → GPT-4o-mini")
                structured = await extract_from_text(raw_text, industry)
            else:
                logger.info(f"[{invoice_id}] Scanned PDF → GPT-4o Vision")
                raw_text, structured = await extract_from_image(file_bytes, "image/png", industry)
        else:
            logger.info(f"[{invoice_id}] Image → GPT-4o Vision")
            raw_text, structured = await extract_from_image(file_bytes, mime_type, industry)

    except Exception as e:
        logger.error(f"[{invoice_id}] Extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Document processing failed. Please try again.")

    # ── Validate ──────────────────────────────────────────────────────────────
    warnings = validate_document(structured)

    # ── Save to Supabase ──────────────────────────────────────────────────────
    supabase = get_supabase()

    # Storage — file goes to: invoices/{user_id}/{invoice_id}/{filename}
    file_path = f"{current_user.id}/{invoice_id}/{file.filename}"
    try:
        supabase.storage.from_("invoices").upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": mime_type}
        )
        logger.info(f"[{invoice_id}] Stored at {file_path}")
    except Exception as e:
        logger.warning(f"[{invoice_id}] Storage upload failed (non-fatal): {e}")
        file_path = ""

    # DB record
    try:
        supabase.table("invoices").insert({
            "id": invoice_id,
            "user_id": current_user.id,        # real UUID from JWT
            "file_url": file_path,
            "file_name": file.filename,
            "file_type": "pdf" if mime_type == "application/pdf" else "image",
            "industry": industry,
            "document_type": structured.document_type,
            "raw_text": raw_text,
            "structured_data": structured.model_dump(),
            "status": "done",
            "validation_warnings": warnings,
        }).execute()
        logger.info(f"[{invoice_id}] Saved to DB")
    except Exception as e:
        logger.error(f"[{invoice_id}] DB save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save document record.")

    # ── Increment usage AFTER successful save ─────────────────────────────────
    await increment_usage(current_user.id)

    logger.info(f"[{invoice_id}] Done | warnings={len(warnings)} | confidence={structured.extraction_confidence}")

    return UploadResponse(
        invoice_id=invoice_id,
        status="done",
        document_type=structured.document_type,
        structured_data=structured,
        validation_warnings=warnings,
    )