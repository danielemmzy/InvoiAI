import logging
from fastapi import APIRouter, HTTPException, Request
from app.core.limiter import limiter
from app.core.supabase import get_supabase
from app.models.invoice import UploadResponse, StructuredDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoice", tags=["Invoice"])


@router.get("/{invoice_id}", response_model=UploadResponse)
@limiter.limit("60/minute")
async def get_invoice(request: Request, invoice_id: str):
    supabase = get_supabase()

    try:
        result = (
            supabase.table("invoices")
            .select("*")
            .eq("id", invoice_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error(f"DB fetch failed for {invoice_id}: {e}")
        raise HTTPException(status_code=404, detail="Document not found")

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    d = result.data

    return UploadResponse(
        invoice_id=d["id"],
        status=d["status"],
        document_type=d.get("document_type"),
        structured_data=StructuredDocument(**d["structured_data"]) if d.get("structured_data") else None,
        validation_warnings=d.get("validation_warnings") or [],
    )


@router.delete("/{invoice_id}")
@limiter.limit("30/minute")
async def delete_invoice(request: Request, invoice_id: str, user_id: str = "test-user"):
    supabase = get_supabase()

    result = (
        supabase.table("invoices")
        .select("user_id, file_url")
        .eq("id", invoice_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    if result.data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if result.data.get("file_url"):
        try:
            supabase.storage.from_("invoices").remove([result.data["file_url"]])
        except Exception as e:
            logger.warning(f"Storage delete failed (non-fatal): {e}")

    supabase.table("invoices").delete().eq("id", invoice_id).execute()

    return {"message": "Deleted successfully"}