from unittest.mock import AsyncMock
import pytest
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app2.services.finance.planning_service import PlanningService
from app2.core.enum.finance import OwnerType


@pytest.mark.asyncio
async def test_planning_service_deterministic_allocation():
    recurring = SimpleNamespace(amount=Decimal("300"))
    debt = SimpleNamespace(minimum_payment=Decimal("100"), interest_rate=20, name="Card")

    recurring_repo = SimpleNamespace(list_active=AsyncMock(return_value=[recurring]))
    debt_repo = SimpleNamespace(list_for_owner=AsyncMock(return_value=[debt]))
    goal_repo = SimpleNamespace(list_active=AsyncMock(return_value=[SimpleNamespace()]))
    plans = SimpleNamespace(create_plan=AsyncMock(side_effect=lambda p: SimpleNamespace(**p)))

    service = PlanningService(
        recurring_repository=recurring_repo,
        debt_repository=debt_repo,
        goal_repository=goal_repo,
        allocation_repository=plans,
    )

    result = await service.generate_plan(
        OwnerType.PERSONAL, uuid4(), Decimal("2000")
    )

    assert result.plan["total_bills"] == "300"
    assert result.plan["total_minimums"] == "100"
    assert result.plan["available"] == "1600"
    assert result.plan["savings_target"] == "400.00"
    assert result.plan["wants_budget"] == "1200.00"
    assert "Highest-interest debt" in result.advice
    plans.create_plan.assert_awaited_once()
