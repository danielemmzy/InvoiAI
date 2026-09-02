"""
============================================================
Personal Finance Domain Models

Mirrors the tables backing Flow 8 (Personal Finance Logging)
and Flow 9 (Bank Statement Auto-Categorization):

- income_entries
- expenses
- budget_categories
- recurring_items
- debts
- goals
- allocation_plans

All rows carry owner_type/owner_id instead of org_id, since
Personal Mode data belongs to a user directly, not an
organization (see context/organization.py's personal_mode
feature flag).
============================================================
"""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.finance import (
    ExpenseCategory,
    GoalStatus,
    IncomeSource,
    OwnerType,
    RecurringFrequency,
)
from app.models.domain.base import TimestampedEntity

JsonDict = dict[str, Any]


class IncomeEntry(TimestampedEntity):
    """Mirrors income_entries."""

    owner_type: OwnerType
    owner_id: UUID

    amount: Decimal
    currency: str = "USD"
    source: IncomeSource
    description: str | None = None
    received_date: date

    is_recurring: bool = False
    metadata: JsonDict = Field(default_factory=dict)


class Expense(TimestampedEntity):
    """Mirrors expenses."""

    owner_type: OwnerType
    owner_id: UUID

    amount: Decimal
    currency: str = "USD"
    description: str
    category: ExpenseCategory = ExpenseCategory.OTHER
    expense_date: date

    document_id: UUID | None = None
    """Set when the expense came from a categorized bank
    statement transaction (Flow 9) rather than a chat message."""

    metadata: JsonDict = Field(default_factory=dict)


class BudgetCategory(TimestampedEntity):
    """Mirrors budget_categories."""

    owner_type: OwnerType
    owner_id: UUID

    category: ExpenseCategory
    monthly_limit: Decimal
    spent: Decimal = Decimal("0")
    period_month: date
    """First day of the month this budget row tracks."""


class RecurringItem(TimestampedEntity):
    """Mirrors recurring_items (bills)."""

    owner_type: OwnerType
    owner_id: UUID

    name: str
    amount: Decimal
    frequency: RecurringFrequency
    next_due_date: date
    is_active: bool = True


class Debt(TimestampedEntity):
    """Mirrors debts."""

    owner_type: OwnerType
    owner_id: UUID

    name: str
    balance: Decimal
    interest_rate: Decimal
    """Annual percentage rate, e.g. 24.00 for 24% APR."""
    minimum_payment: Decimal


class Goal(TimestampedEntity):
    """Mirrors goals."""

    owner_type: OwnerType
    owner_id: UUID

    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0")
    target_date: date | None = None
    status: GoalStatus = GoalStatus.ACTIVE


class AllocationPlan(TimestampedEntity):
    """
    Mirrors allocation_plans — the pure-Python output of
    PlanningService.generate_plan(), never LLM-generated.
    """

    owner_type: OwnerType
    owner_id: UUID

    income: Decimal
    plan: JsonDict = Field(default_factory=dict)
    """
    {
      "total_bills": ..., "total_minimums": ...,
      "available": ..., "savings_target": ...,
      "wants_budget": ...
    }
    """
    advice: str | None = None
