"""
============================================================
app/repositories/organization/usage_repository.py

Organization Usage Repository

Responsibilities:
- Monthly usage
- Plan usage
- Usage metrics
- Usage persistence

No business logic.
No authorization.
No FastAPI.
============================================================
"""

from datetime import date
from typing import Any

from app.repositories.base import BaseRepository


class UsageRepository(BaseRepository):

    TABLE = "organization_usage"

    # ---------------------------------------------------------
    # Get Current Month Usage
    # ---------------------------------------------------------

    async def get_current_usage(
        self,
        org_id: str,
        month: str,
    ) -> dict | None:

        result = (
            self.db.table(self.TABLE)
            .select("*")
            .eq("org_id", org_id)
            .eq("month", month)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]

    # ---------------------------------------------------------
    # Create Monthly Usage
    # ---------------------------------------------------------

    async def create_month(
        self,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.db.table(self.TABLE)
            .insert(values)
            .execute()
        )

        return result.data[0]

    # ---------------------------------------------------------
    # Update Usage Record
    # ---------------------------------------------------------

    async def update_usage(
        self,
        org_id: str,
        month: str,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.db.table(self.TABLE)
            .update(values)
            .eq("org_id", org_id)
            .eq("month", month)
            .execute()
        )

        return result.data[0]

    # ---------------------------------------------------------
    # Update Usage Metrics (Atomic)
    # ---------------------------------------------------------

    async def update_usage_metrics(
        self,
        *,
        org_id: str,
        month: str,
        user_id: str | None = None,
        document_increment: int = 0,
        storage_increment: int = 0,
        ai_tokens_increment: int = 0,
        api_calls_increment: int = 0,
        ai_cost_increment: float = 0,
    ) -> None:
        """
        Atomically updates organization usage.
        """

        await self.db.rpc(
        "usage_update_metrics",
        {
            "p_org_id": org_id,
            "p_month": month,
            "p_document_increment": document_increment,
            "p_storage_increment": storage_increment,
            "p_ai_tokens_increment": ai_tokens_increment,
            "p_api_calls_increment": api_calls_increment,
            "p_ai_cost_increment": ai_cost_increment,
            "p_user_id": user_id,
        },
    ).execute()

    # ---------------------------------------------------------
    # Delete Month
    # ---------------------------------------------------------

    async def delete_month(
        self,
        org_id: str,
        month: str,
    ) -> None:

        (
            self.db.table(self.TABLE)
            .delete()
            .eq("org_id", org_id)
            .eq("month", month)
            .execute()
        )

    # ---------------------------------------------------------
    # Helper
    # ---------------------------------------------------------

    @staticmethod
    def current_month() -> str:
        return date.today().strftime("%Y-%m")