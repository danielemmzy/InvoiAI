"""
============================================================
Personal Finance Schemas

API request/response models for routers/finance.py.
============================================================
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enum.finance import (
    ExpenseCategory,
    GoalStatus,
    IncomeSource,
    RecurringFrequency,
)


# ============================================================
# Income
# ============================================================

class IncomeCreate(BaseModel):
    amount: Decimal
    currency: str = "USD"
    source: IncomeSource = IncomeSource.SALARY
    description: str | None = None
    received_date: date | None = None
    is_recurring: bool = False


class IncomeResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    source: IncomeSource
    description: str | None = None
    received_date: date
    is_recurring: bool
    created_at: datetime


# ============================================================
# Expense
# ============================================================

class ExpenseCreate(BaseModel):
    amount: Decimal
    currency: str = "USD"
    description: str
    category: ExpenseCategory | None = None
    """If omitted, ExpenseService auto-detects a category from
    the description (matches Flow 8's 'category auto-detected'
    step)."""
    expense_date: date | None = None


class ExpenseResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    description: str
    category: ExpenseCategory
    expense_date: date
    created_at: datetime


# ============================================================
# Budget
# ============================================================

class BudgetCategoryResponse(BaseModel):
    id: UUID
    category: ExpenseCategory
    monthly_limit: Decimal
    spent: Decimal
    period_month: date


class BudgetSummaryResponse(BaseModel):
    period_month: date
    categories: list[BudgetCategoryResponse]
    total_limit: Decimal
    total_spent: Decimal


# ============================================================
# Recurring items / Debts / Goals (read-only for now — creation
# happens via the copilot tools or a future settings page)
# ============================================================

class RecurringItemResponse(BaseModel):
    id: UUID
    name: str
    amount: Decimal
    frequency: RecurringFrequency
    next_due_date: date
    is_active: bool


class DebtResponse(BaseModel):
    id: UUID
    name: str
    balance: Decimal
    interest_rate: Decimal
    minimum_payment: Decimal


class GoalResponse(BaseModel):
    id: UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date | None = None
    status: GoalStatus


# ============================================================
# Allocation Plan
# ============================================================

class AllocationPlanResponse(BaseModel):
    id: UUID
    income: Decimal
    plan: dict[str, Any] = Field(default_factory=dict)
    advice: str | None = None
    created_at: datetime
