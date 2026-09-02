from unittest.mock import AsyncMock
import pytest
from uuid import uuid4
from types import SimpleNamespace

from app2.services.ai.tool_executor_service import ToolExecutor


@pytest.mark.asyncio
async def test_copilot_tool_executor_routes_personal_tools_without_llm_math():
    income = SimpleNamespace(id=uuid4())
    plan = SimpleNamespace(plan={"available":"100"}, advice="deterministic")
    income_service = SimpleNamespace(create=AsyncMock(return_value=income))
    planning = SimpleNamespace(generate_plan=AsyncMock(return_value=plan))

    executor = ToolExecutor(
        income_service=income_service,
        planning_service=planning,
    )

    user_id = uuid4()
    result = await executor.execute(
        tool_name="record_paycheck",
        arguments={"amount": 1000, "source": "salary"},
        user_id=user_id,
    )

    assert result["amount"] == 1000
    assert result["plan"] == {"available":"100"}
    income_service.create.assert_awaited_once()
    planning.generate_plan.assert_awaited_once()
