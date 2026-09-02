from unittest.mock import AsyncMock
import pytest
from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace

from app2.services.approval.approval_step_service import ApprovalStepService
from app2.core.enum.database import OrgRole


@pytest.mark.asyncio
async def test_create_approval_step_enforces_positive_step_and_persists():
    repo = SimpleNamespace()
    repo.create_step = AsyncMock(return_value=SimpleNamespace(id=uuid4()))

    service = ApprovalStepService(repo)

    with pytest.raises(ValueError):
        await service.create_step(
            workflow_id=uuid4(),
            org_id=uuid4(),
            step_number=0,
            step_name="Manager",
            approver_id=uuid4(),
            approver_role=OrgRole.ADMIN,
        )

    created = await service.create_step(
        workflow_id=uuid4(),
        org_id=uuid4(),
        step_number=1,
        step_name="Manager",
        approver_id=uuid4(),
        approver_role=OrgRole.ADMIN,
        spending_limit=Decimal("1000"),
    )
    assert created is not None
    repo.create_step.assert_awaited_once()
