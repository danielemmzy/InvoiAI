from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.db import execute
from app.core.supabase import get_supabase


class FXRateRepository:
    table_name = "fx_rates"

    def __init__(self, db=None):
        self.db = db or get_supabase()

    async def get_rates(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        response = await execute(
            self.db.table(self.table_name)
            .select("base_currency,quote_currency,rate,rate_date,source,is_forward_filled")
            .eq("base_currency", base_currency)
            .eq("quote_currency", quote_currency)
            .gte("rate_date", date_from.isoformat())
            .lte("rate_date", date_to.isoformat())
            .order("rate_date")
        )
        return response.data or []

    async def upsert_rates(self, rows: list[dict]) -> None:
        if not rows:
            return
        await execute(
            self.db.table(self.table_name).upsert(
                rows,
                on_conflict="base_currency,quote_currency,rate_date,source",
            )
        )
