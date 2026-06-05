import logging
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from app.core.limiter import limiter
from app.core.auth import get_current_user, AuthUser
from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])


@router.get("")
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
    industry: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
):
    """
    Paginated document history for the authenticated user.
    Optionally filter by industry.
    Requires: Authorization: Bearer <access_token>

    Only returns the user's own documents — enforced by .eq("user_id").
    Lightweight query — no structured_data blob, just metadata.
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("invoices")
            .select(
                "id, file_name, file_type, industry, document_type, "
                "status, validation_warnings, created_at"
            )
            .eq("user_id", current_user.id)    # only their documents
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if industry:
            query = query.eq("industry", industry)

        result = query.execute()

    except Exception as e:
        logger.error(f"History fetch failed for {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")

    return {
        "documents": result.data,
        "count": len(result.data),
        "offset": offset,
        "limit": limit,
    }