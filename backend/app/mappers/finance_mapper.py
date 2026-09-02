"""
============================================================
Personal Finance Mappers

One mapper per finance domain model, following the same
one-class pattern as mappers/vendor_mapper.py — grouped into
a single file since they're small and share this domain
(same precedent as mappers/integration_mapper.py holding two
classes).
============================================================
"""

from app.mappers.base import BaseMapper
from app.models.domain.finance import (
    AllocationPlan,
    BudgetCategory,
    Debt,
    Expense,
    Goal,
    IncomeEntry,
    RecurringItem,
)
from app.schemas.finance import (
    AllocationPlanResponse,
    BudgetCategoryResponse,
    DebtResponse,
    ExpenseResponse,
    GoalResponse,
    IncomeResponse,
    RecurringItemResponse,
)


class IncomeEntryMapper(BaseMapper[IncomeEntry, IncomeResponse]):
    domain_model = IncomeEntry
    response_model = IncomeResponse


class ExpenseMapper(BaseMapper[Expense, ExpenseResponse]):
    domain_model = Expense
    response_model = ExpenseResponse


class BudgetCategoryMapper(BaseMapper[BudgetCategory, BudgetCategoryResponse]):
    domain_model = BudgetCategory
    response_model = BudgetCategoryResponse


class RecurringItemMapper(BaseMapper[RecurringItem, RecurringItemResponse]):
    domain_model = RecurringItem
    response_model = RecurringItemResponse


class DebtMapper(BaseMapper[Debt, DebtResponse]):
    domain_model = Debt
    response_model = DebtResponse


class GoalMapper(BaseMapper[Goal, GoalResponse]):
    domain_model = Goal
    response_model = GoalResponse


class AllocationPlanMapper(BaseMapper[AllocationPlan, AllocationPlanResponse]):
    domain_model = AllocationPlan
    response_model = AllocationPlanResponse
