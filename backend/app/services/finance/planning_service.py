"""
============================================================
Planning Service

Flow 8 — "planning_service.generate_plan(owner_id) — NO LLM"

Reads recurring_items, debts, budget_categories, and goals,
then computes an allocation plan with plain arithmetic. The
copilot's LLM only ever narrates this output in plain English
(see services/ai/tools/personal_tools.py) — it never performs
the math itself.

MIGRATION NOTE: this service depends on 6 new tables that do
not exist yet in your Supabase schema:
  income_entries, expenses, budget_categories,
  recurring_items, debts, goals, allocation_plans
Each needs owner_type (text/enum: 'organization'|'personal')
and owner_id (uuid) columns, matching app/core/enum/finance.py.
============================================================
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.core.enum.finance import OwnerType
from app.repositories.finance.finance_repository import (
    AllocationPlanRepository,
    DebtRepository,
    GoalRepository,
    RecurringItemRepository,
    BudgetRepository,
)

SAVINGS_RATE = Decimal("0.20")


class PlanningService:
    def __init__(
        self,
        recurring_repository: RecurringItemRepository | None = None,
        debt_repository: DebtRepository | None = None,
        goal_repository: GoalRepository | None = None,
        allocation_repository: AllocationPlanRepository | None = None,
    ) -> None:
        self.recurring = recurring_repository or RecurringItemRepository()
        self.debts = debt_repository or DebtRepository()
        self.goals = goal_repository or GoalRepository()
        self.plans = allocation_repository or AllocationPlanRepository()
        self.budget_repository = BudgetRepository()


    async def budget_for_period(self, owner_type: OwnerType, owner_id: UUID, period_month):
        return await self.budget_repository.list_for_period(owner_type, owner_id, period_month)

    async def latest_plan(self, owner_type: OwnerType, owner_id: UUID):
        return await self.plans.latest_for_owner(owner_type, owner_id)

    async def recurring_items(self, owner_type: OwnerType, owner_id: UUID):
        return await self.recurring.list_active(owner_type, owner_id)

    async def debts(self, owner_type: OwnerType, owner_id: UUID):
        return await self.debts.list_for_owner(owner_type, owner_id)

    async def goals(self, owner_type: OwnerType, owner_id: UUID):
        return await self.goals.list_active(owner_type, owner_id)

    async def generate_plan(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
        income: Decimal,
    ):
        recurring_items = await self.recurring.list_active(owner_type, owner_id)
        debts = await self.debts.list_for_owner(owner_type, owner_id)
        active_goals = await self.goals.list_active(owner_type, owner_id)

        total_bills = sum(
            (item.amount for item in recurring_items), Decimal("0")
        )
        total_minimums = sum(
            (debt.minimum_payment for debt in debts), Decimal("0")
        )

        available = income - total_bills - total_minimums

        has_goal = len(active_goals) > 0
        savings_target = (income * SAVINGS_RATE) if has_goal else Decimal("0")

        wants_budget = available - savings_target
        if wants_budget < Decimal("0"):
            wants_budget = Decimal("0")

        plan = {
            "total_bills": str(total_bills),
            "total_minimums": str(total_minimums),
            "available": str(available),
            "savings_target": str(savings_target),
            "wants_budget": str(wants_budget),
            "bill_count": len(recurring_items),
            "debt_count": len(debts),
            "active_goal_count": len(active_goals),
        }

        advice = self._build_advice(
            income=income,
            total_bills=total_bills,
            total_minimums=total_minimums,
            available=available,
            savings_target=savings_target,
            wants_budget=wants_budget,
            debts=debts,
        )

        return await self.plans.create_plan(
            {
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "income": income,
                "plan": plan,
                "advice": advice,
            }
        )

    @staticmethod
    def _build_advice(
        *,
        income: Decimal,
        total_bills: Decimal,
        total_minimums: Decimal,
        available: Decimal,
        savings_target: Decimal,
        wants_budget: Decimal,
        debts,
    ) -> str:
        """
        Deterministic plain-English summary. The copilot LLM may
        further rephrase this, but the numbers themselves are
        computed here, not by the model — matching the doc's
        "LLM NEVER calculated anything" principle from Flow 7.
        """
        lines = [
            f"Income of {income} against known bills of {total_bills} "
            f"and debt minimums of {total_minimums} leaves {available} available."
        ]

        if debts:
            highest = max(debts, key=lambda d: d.interest_rate)
            lines.append(
                f"Highest-interest debt is '{highest.name}' at "
                f"{highest.interest_rate}% APR — consider extra "
                f"payments there first."
            )

        if savings_target > 0:
            lines.append(
                f"Recommended: {savings_target} to savings, "
                f"{wants_budget} for flexible spending."
            )
        else:
            lines.append(
                f"No active savings goal set — {wants_budget} is "
                f"free to allocate."
            )

        return " ".join(lines)
