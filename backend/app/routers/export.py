import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from app.core.limiter import limiter
from app.core.auth import get_current_user, AuthUser
from app.core.supabase import get_supabase
from app.services.exporter import export_to_excel, export_to_csv
from app.services.sheets import export_to_sheets
from app.models.invoice import StructuredDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/{invoice_id}/excel")
@limiter.limit("20/minute")
async def download_excel(
    request: Request,
    invoice_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Downloads invoice as a formatted Excel file.
    Dynamic sheets — one per section GPT extracted.
    Requires: Authorization: Bearer <access_token>
    """
    structured, file_name = await _fetch_structured(invoice_id, current_user.id)
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
async def download_csv(
    request: Request,
    invoice_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Downloads invoice as CSV.
    Requires: Authorization: Bearer <access_token>
    """
    structured, file_name = await _fetch_structured(invoice_id, current_user.id)
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


@router.post("/{invoice_id}/sheets")
@limiter.limit("10/minute")
async def export_to_google_sheets(
    request: Request,
    invoice_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Creates a Google Sheets spreadsheet from the invoice data.
    Shares it with the user's email address.
    Returns the spreadsheet URL.

    Requires: Authorization: Bearer <access_token>

    Flow:
    1. Fetch structured data from DB
    2. Create Google Spreadsheet via service account
    3. Fill all sections with data + formatting
    4. Share spreadsheet with user's email
    5. Save sheets_url to DB (so user can re-access it later)
    6. Return URL to frontend

    The sheet is owned by the InvoiAI service account but
    the user has "writer" access — they can edit it freely.
    """
    structured, file_name = await _fetch_structured(invoice_id, current_user.id)

    # Check if already exported to sheets
    # Return existing URL instead of creating a duplicate
    supabase = get_supabase()
    existing = (
        supabase.table("invoices")
        .select("sheets_url")
        .eq("id", invoice_id)
        .single()
        .execute()
    )

    if existing.data and existing.data.get("sheets_url"):
        logger.info(f"Returning existing sheets URL for {invoice_id}")
        return {
            "sheets_url": existing.data["sheets_url"],
            "message": "Existing spreadsheet returned"
        }

    # Create new spreadsheet
    try:
        sheets_url = await export_to_sheets(
            doc=structured,
            user_email=current_user.email,
            document_name=file_name,
        )
    except Exception as e:
        logger.error(f"Sheets export failed for {invoice_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Google Sheets export failed. Please try again."
        )

    # Save URL to DB so user can access it again from history
    try:
        supabase.table("invoices").update(
            {"sheets_url": sheets_url}
        ).eq("id", invoice_id).execute()
    except Exception as e:
        logger.warning(f"Failed to save sheets_url (non-fatal): {e}")

    logger.info(f"Sheets export complete for {invoice_id}: {sheets_url}")

    return {
        "sheets_url": sheets_url,
        "message": "Spreadsheet created and shared with your email"
    }


async def _fetch_structured(
    invoice_id: str,
    user_id: str
) -> tuple[StructuredDocument, str]:
    """
    Fetches structured_data and file_name from DB.
    Ownership check included — users only access their own invoices.
    """
    supabase = get_supabase()

    try:
        result = (
            supabase.table("invoices")
            .select("structured_data, status, user_id, file_name")
            .eq("id", invoice_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error(f"Export fetch failed for {invoice_id}: {e}")
        raise HTTPException(status_code=404, detail="Document not found")

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    if result.data["status"] != "done":
        raise HTTPException(status_code=400, detail="Document still processing")

    return (
        StructuredDocument(**result.data["structured_data"]),
        result.data.get("file_name", "document")
    )