from datetime import datetime
from fastapi import HTTPException, status
from app.core.supabase import get_supabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_current_month() -> str:
    return datetime.now().strftime("%Y-%m")


async def check_usage_limit(user_id: str, plan: str) -> None:
    """
    Checks monthly limit BEFORE processing.
    Raises 429 if limit hit — saves OpenAI API cost.
    """
    limit = settings.plan_limits.get(plan, 10)
    month = get_current_month()
    supabase = get_supabase()

    try:
        result = (
            supabase.table("usage")
            .select("invoice_count")
            .eq("user_id", user_id)
            .eq("month", month)
            .single()
            .execute()
        )
        current_count = result.data.get("invoice_count", 0) if result.data else 0
    except Exception:
        current_count = 0

    logger.info(f"User {user_id} | usage={current_count}/{limit} | plan={plan}")

    if current_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly limit reached. You have used {current_count}/{limit} "
                f"documents on the {plan} plan. Please upgrade to continue."
            )
        )


async def increment_usage(user_id: str) -> None:
    """
    Increments monthly count AFTER successful processing.
    Non-fatal if it fails — document already saved.
    """
    month = get_current_month()
    supabase = get_supabase()

    try:
        result = (
            supabase.table("usage")
            .select("invoice_count")
            .eq("user_id", user_id)
            .eq("month", month)
            .single()
            .execute()
        )

        if result.data:
            supabase.table("usage").update(
                {"invoice_count": result.data["invoice_count"] + 1}
            ).eq("user_id", user_id).eq("month", month).execute()
        else:
            supabase.table("usage").insert({
                "user_id": user_id,
                "month": month,
                "invoice_count": 1,
            }).execute()

        logger.info(f"Usage incremented for {user_id} month={month}")

    except Exception as e:
        logger.error(f"Failed to increment usage for {user_id}: {e}")


async def get_usage_summary(user_id: str, plan: str) -> dict:
    """Returns usage summary shown in the user's profile."""
    month = get_current_month()
    limit = settings.plan_limits.get(plan, 10)
    supabase = get_supabase()

    try:
        result = (
            supabase.table("usage")
            .select("invoice_count")
            .eq("user_id", user_id)
            .eq("month", month)
            .single()
            .execute()
        )
        used = result.data.get("invoice_count", 0) if result.data else 0
    except Exception:
        used = 0

    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "plan": plan,
        "month": month,
        "limit_reached": used >= limit,
    }