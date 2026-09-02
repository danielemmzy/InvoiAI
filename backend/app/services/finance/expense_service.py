"""
============================================================
Expense Service

Flow 8 — "Tool 2/3: log_expense(45, 'fuel')" ->
expense_service.create(), with "category auto-detected".

Category detection is deliberately pure keyword matching, not
an LLM call — matches the pipeline doc's "NO LLM" emphasis for
the deterministic parts of personal finance. The copilot's LLM
layer only ever decides *which tool to call*; this service
decides *how to file it*.
============================================================
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.enum.finance import ExpenseCategory, OwnerType
from app.repositories.finance.finance_repository import (
    BudgetRepository,
    ExpenseRepository,
)

# Keyword -> category. Checked as a case-insensitive substring
# match against the expense description. Order matters: first
# match wins, so more specific keywords are listed first.
_CATEGORY_KEYWORDS: list[tuple[str, ExpenseCategory]] = [
    ("netflix", ExpenseCategory.SUBSCRIPTIONS),
    ("spotify", ExpenseCategory.SUBSCRIPTIONS),
    ("subscription", ExpenseCategory.SUBSCRIPTIONS),
    ("prime video", ExpenseCategory.SUBSCRIPTIONS),
    ("fuel", ExpenseCategory.TRANSPORT),
    ("petrol", ExpenseCategory.TRANSPORT),
    ("gas station", ExpenseCategory.TRANSPORT),
    ("uber", ExpenseCategory.TRANSPORT),
    ("bolt", ExpenseCategory.TRANSPORT),
    ("taxi", ExpenseCategory.TRANSPORT),
    ("rent", ExpenseCategory.HOUSING),
    ("mortgage", ExpenseCategory.HOUSING),
    ("electricity", ExpenseCategory.UTILITIES),
    ("water bill", ExpenseCategory.UTILITIES),
    ("internet", ExpenseCategory.UTILITIES),
    ("grocery", ExpenseCategory.FOOD),
    ("groceries", ExpenseCategory.FOOD),
    ("restaurant", ExpenseCategory.FOOD),
    ("supermarket", ExpenseCategory.FOOD),
    ("credit card", ExpenseCategory.DEBT_PAYMENT),
    ("loan payment", ExpenseCategory.DEBT_PAYMENT),
    ("pharmacy", ExpenseCategory.HEALTHCARE),
    ("clinic", ExpenseCategory.HEALTHCARE),
    ("hospital", ExpenseCategory.HEALTHCARE),
    ("cinema", ExpenseCategory.ENTERTAINMENT),
    ("movie", ExpenseCategory.ENTERTAINMENT),
    ("tuition", ExpenseCategory.EDUCATION),
    ("school fees", ExpenseCategory.EDUCATION),
    ("insurance", ExpenseCategory.INSURANCE),
]


def detect_category(description: str) -> ExpenseCategory:
    text = description.lower()
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in text:
            return category
    return ExpenseCategory.OTHER


class ExpenseService:
    def __init__(
        self,
        repository: ExpenseRepository | None = None,
        budget_repository: BudgetRepository | None = None,
    ) -> None:
        self.repository = repository or ExpenseRepository()
        self.budgets = budget_repository or BudgetRepository()

    async def create(
        self,
        *,
        owner_type: OwnerType,
        owner_id: UUID,
        amount: Decimal,
        description: str,
        category: ExpenseCategory | None = None,
        currency: str = "USD",
        expense_date: date | None = None,
        document_id: UUID | None = None,
    ):
        resolved_category = category or detect_category(description)
        effective_date = expense_date or datetime.now(timezone.utc).date()

        expense = await self.repository.create_expense(
            {
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "amount": amount,
                "currency": currency,
                "description": description,
                "category": resolved_category.value,
                "expense_date": effective_date.isoformat(),
                "document_id": document_id,
            }
        )

        await self._recalculate_budget(
            owner_type,
            owner_id,
            resolved_category,
            effective_date,
        )

        return expense

    async def _recalculate_budget(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        category: ExpenseCategory,
        as_of: date,
    ) -> None:
        """
        Matches Flow 9's "Budget tracking updated automatically:
        budget_categories.spent recalculated for this month".
        """
        period_month = as_of.replace(day=1)
        month_end = (
            period_month.replace(month=period_month.month % 12 + 1)
            if period_month.month < 12
            else period_month.replace(year=period_month.year + 1, month=1)
        )

        totals = await self.repository.sum_by_category_for_month(
            owner_type,
            owner_id,
            period_month,
            month_end,
        )
        spent = totals.get(category.value, 0.0)

        budget = await self.budgets.get_or_create_period(
            owner_type,
            owner_id,
            category.value,
            period_month,
            default_limit=0,
        )
        if budget is not None:
            await self.budgets.update_spent(budget.id, spent)

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
