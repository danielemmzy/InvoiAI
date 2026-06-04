import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from app.core.limiter import limiter
from app.core.supabase import get_supabase
from app.services.exporter import export_to_excel, export_to_csv
from app.models.invoice import StructuredDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/{invoice_id}/excel")
@limiter.limit("20/minute")
async def download_excel(request: Request, invoice_id: str):
    structured = await _fetch_structured(invoice_id)
    excel_bytes = export_to_excel(structured)

    filename = (
        f"invoiai_{structured.document_type.lower().replace(' ', '_')}"
        f"_{invoice_id[:8]}.xlsx"
    )

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{invoice_id}/csv")
@limiter.limit("20/minute")
async def download_csv(request: Request, invoice_id: str):
    structured = await _fetch_structured(invoice_id)
    csv_bytes = export_to_csv(structured)

    filename = (
        f"invoiai_{structured.document_type.lower().replace(' ', '_')}"
        f"_{invoice_id[:8]}.csv"
    )

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def _fetch_structured(invoice_id: str) -> StructuredDocument:
    supabase = get_supabase()

    try:
        result = (
            supabase.table("invoices")
            .select("structured_data, status, document_type")
            .eq("id", invoice_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error(f"Export DB fetch failed for {invoice_id}: {e}")
        raise HTTPException(status_code=404, detail="Document not found")

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    if result.data["status"] != "done":
        raise HTTPException(status_code=400, detail="Document still processing")

    return StructuredDocument(**result.data["structured_data"])