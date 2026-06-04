import logging
from fastapi import APIRouter, HTTPException, Query, Request
from app.core.limiter import limiter
from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])


@router.get("")
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    user_id: str = "test-user",
    industry: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
):
    supabase = get_supabase()

    try:
        query = (
            supabase.table("invoices")
            .select(
                "id, file_name, file_type, industry, document_type, "
                "status, validation_warnings, created_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if industry:
            query = query.eq("industry", industry)

        result = query.execute()

    except Exception as e:
        logger.error(f"History fetch failed for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")

    return {
        "documents": result.data,
        "count": len(result.data),
        "offset": offset,
        "limit": limit,
    }