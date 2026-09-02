"""
============================================================
Income Service

Flow 8 — "Tool 1: record_paycheck(2400)" -> income_service.create().

No SQL. No AI. Pure persistence + a thin read API.
============================================================
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.enum.finance import IncomeSource, OwnerType
from app.repositories.finance.finance_repository import IncomeRepository


class IncomeService:
    def __init__(
        self,
        repository: IncomeRepository | None = None,
    ) -> None:
        self.repository = repository or IncomeRepository()

    async def create(
        self,
        *,
        owner_type: OwnerType,
        owner_id: UUID,
        amount: Decimal,
        source: IncomeSource = IncomeSource.SALARY,
        currency: str = "USD",
        description: str | None = None,
        received_date: date | None = None,
        is_recurring: bool = False,
    ):
        return await self.repository.create_income(
            {
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "amount": amount,
                "currency": currency,
                "source": source.value,
                "description": description,
                "received_date": (
                    received_date or datetime.now(timezone.utc).date()
                ).isoformat(),
                "is_recurring": is_recurring,
            }
        )

    async def list_for_owner(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self.repository.list_for_owner(
            owner_type,
            owner_id,
            limit,
            offset,
        )

    async def month_total(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        month_start: date,
        month_end: date,
    ) -> float:
        return await self.repository.sum_for_month(
            owner_type,
            owner_id,
            month_start,
            month_end,
        )
