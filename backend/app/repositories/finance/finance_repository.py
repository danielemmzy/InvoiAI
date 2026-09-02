"""
============================================================
Personal Finance Repositories

Persistence for:

- income_entries
- expenses
- budget_categories
- recurring_items
- debts
- goals
- allocation_plans

Grouped in one file the same way
repositories/integration/integration_repository.py holds both
IntegrationConnectionRepository and IntegrationSyncRepository.

All queries are owner-scoped (owner_type + owner_id) rather
than org-scoped, since Personal Mode data belongs to a user
directly.
============================================================
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.core.enum.finance import OwnerType
from app.mappers.finance_mapper import (
    AllocationPlanMapper,
    BudgetCategoryMapper,
    DebtMapper,
    ExpenseMapper,
    GoalMapper,
    IncomeEntryMapper,
    RecurringItemMapper,
)
from app.repositories.base import BaseRepository


class IncomeRepository(BaseRepository):
    table_name = "income_entries"
    mapper = IncomeEntryMapper

    async def create_income(self, data):
        return await self.create(data)

    async def list_for_owner(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .order("received_date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return self._many(response)

    async def sum_for_month(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        month_start: date,
        month_end: date,
    ) -> float:
        response = (
            self.table()
            .select("amount")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .gte("received_date", month_start.isoformat())
            .lte("received_date", month_end.isoformat())
            .execute()
        )
        rows = self.raw_many(response)
        return sum(float(r.get("amount", 0)) for r in rows)


class ExpenseRepository(BaseRepository):
    table_name = "expenses"
    mapper = ExpenseMapper

    async def create_expense(self, data):
        return await self.create(data)

    async def list_for_owner(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .order("expense_date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return self._many(response)

    async def list_for_month(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        month_start: date,
        month_end: date,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .gte("expense_date", month_start.isoformat())
            .lte("expense_date", month_end.isoformat())
            .execute()
        )
        return self._many(response)

    async def sum_by_category_for_month(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        month_start: date,
        month_end: date,
    ) -> dict[str, float]:
        rows = self.raw_many(
            self.table()
            .select("category, amount")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .gte("expense_date", month_start.isoformat())
            .lte("expense_date", month_end.isoformat())
            .execute()
        )
        totals: dict[str, float] = {}
        for row in rows:
            category = row.get("category", "other")
            totals[category] = totals.get(category, 0.0) + float(row.get("amount", 0))
        return totals


class BudgetRepository(BaseRepository):
    table_name = "budget_categories"
    mapper = BudgetCategoryMapper

    async def get_or_create_period(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        category: str,
        period_month: date,
        default_limit,
    ):
        existing = self.raw_many(
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .eq("category", category)
            .eq("period_month", period_month.isoformat())
            .limit(1)
            .execute()
        )
        if existing:
            return self.mapper.to_domain(existing[0])

        return await self.create(
            {
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "category": category,
                "monthly_limit": default_limit,
                "spent": 0,
                "period_month": period_month.isoformat(),
            }
        )

    async def list_for_period(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        period_month: date,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .eq("period_month", period_month.isoformat())
            .execute()
        )
        return self._many(response)

    async def update_spent(
        self,
        budget_id: UUID,
        spent,
    ):
        return await self.update(budget_id, {"spent": spent})


    async def list_all_for_period(
        self,
        period_month: date,
        *,
        limit: int = 5000,
    ):
        response = (
            self.table()
            .select("*")
            .eq("period_month", period_month.isoformat())
            .order("owner_type")
            .order("owner_id")
            .limit(limit)
            .execute()
        )
        return self._many(response)


class RecurringItemRepository(BaseRepository):
    table_name = "recurring_items"
    mapper = RecurringItemMapper

    async def list_active(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .eq("is_active", True)
            .execute()
        )
        return self._many(response)


    async def list_all_active(
        self,
        *,
        limit: int = 5000,
    ):
        response = (
            self.table()
            .select("*")
            .eq("is_active", True)
            .order("next_due_date")
            .limit(limit)
            .execute()
        )
        return self._many(response)


class DebtRepository(BaseRepository):
    table_name = "debts"
    mapper = DebtMapper

    async def list_for_owner(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .execute()
        )
        return self._many(response)


class GoalRepository(BaseRepository):
    table_name = "goals"
    mapper = GoalMapper

    async def list_active(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .eq("status", "active")
            .execute()
        )
        return self._many(response)


    async def list_all_active(
        self,
        *,
        limit: int = 5000,
    ):
        response = (
            self.table()
            .select("*")
            .eq("status", "active")
            .order("target_date")
            .limit(limit)
            .execute()
        )
        return self._many(response)


class AllocationPlanRepository(BaseRepository):
    table_name = "allocation_plans"
    mapper = AllocationPlanMapper

    async def create_plan(self, data):
        return await self.create(data)

    async def latest_for_owner(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
    ):
        response = (
            self.table()
            .select("*")
            .eq("owner_type", owner_type.value)
            .eq("owner_id", str(owner_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return self._one(response)
