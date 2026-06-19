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
    Checks monthly limit before processing.
    """

    limit = settings.plan_limits.get(plan, 5)
    month = get_current_month()
    supabase = get_supabase()

    try:
        result = (
            supabase.table("usage")
            .select("invoice_count")
            .eq("user_id", user_id)
            .eq("month", month)
            .maybe_single()
            .execute()
        )

        current_count = (
            result.data.get("invoice_count", 0)
            if result.data
            else 0
        )

    except Exception as e:
        logger.error(
            f"Usage lookup failed for {user_id}: {e}"
        )
        current_count = 0

    logger.info(
        f"USAGE CHECK | user={user_id} | used={current_count}/{limit}"
    )

    if current_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly limit reached. "
                f"You have used {current_count}/{limit} documents."
            ),
        )


async def increment_usage(user_id: str) -> None:
    month = get_current_month()
    supabase = get_supabase()

    logger.info(f"INCREMENT START | user={user_id} | month={month}")

    try:
        result = (
            supabase.table("usage")
            .select("*")
            .eq("user_id", user_id)
            .eq("month", month)
            .execute()
        )

        logger.info(f"INCREMENT QUERY RESULT = {result}")

        if result.data and len(result.data) > 0:
            current_count = result.data[0]["invoice_count"]

            logger.info(f"UPDATING ROW {current_count} -> {current_count + 1}")

            update_result = (
                supabase.table("usage")
                .update({"invoice_count": current_count + 1})
                .eq("user_id", user_id)
                .eq("month", month)
                .execute()
            )

            logger.info(f"UPDATE RESULT = {update_result}")

        else:
            logger.info("NO ROW FOUND - CREATING FIRST ROW")

            insert_result = (
                supabase.table("usage")
                .insert({
                    "user_id": user_id,
                    "month": month,
                    "invoice_count": 1
                })
                .execute()
            )

            logger.info(f"INSERT RESULT = {insert_result}")

    except Exception as e:
        logger.error(f"INCREMENT FAILED = {e}")


async def get_usage_summary(user_id: str, plan: str) -> dict:
    month = get_current_month()
    limit = settings.plan_limits.get(plan, 5)
    supabase = get_supabase()

    try:
        result = (
            supabase.table("usage")
            .select("*")
            .eq("user_id", user_id)
            .eq("month", month)
            .execute()
        )

        logger.info(f"RESULT TYPE = {type(result)}")
        logger.info(f"RESULT = {result}")

        if not result:
            used = 0
        elif not result.data:
            used = 0
        else:
            used = result.data[0]["invoice_count"]

    except Exception as e:
        logger.error(f"Usage summary failed: {e}")
        used = 0

    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "plan": plan,
        "month": month,
        "limit_reached": used >= limit,
    }