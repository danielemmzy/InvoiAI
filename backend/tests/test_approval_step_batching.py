"""Creating an approval workflow must insert its steps in one statement."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.enum.application import ApprovalStatus
from app.core.enum.database import ApprovalDecision, DocumentType, OrgRole, RiskLevel
from app.models.domain.approval import ApprovalStep, ApprovalWorkflow
from app.services.approval.approval_engine import ApprovalEngine

ORG = uuid4()
DOC = uuid4()


class WorkflowRepository:
    async def create_workflow(self, workflow):
        return workflow


class StepRepository:
    def __init__(self):
        self.batch_calls = 0
        self.single_calls = 0

    async def create_steps(self, steps):
        self.batch_calls += 1
        self.batch = list(steps)
        return list(steps)

    async def create_step(self, _step):  # pragma: no cover - regression path
        self.single_calls += 1
        raise AssertionError("workflow steps must be inserted in one statement")


class HistoryRepository:
    def __init__(self):
        self.calls = 0

    async def create_history(self, history):
        self.calls += 1
        return history


def _workflow(total_steps: int) -> ApprovalWorkflow:
    return ApprovalWorkflow(
        id=uuid4(),
        org_id=ORG,
        document_id=DOC,
        analysis_id=uuid4(),
        status=ApprovalStatus.PENDING,
        current_step=1,
        total_steps=total_steps,
        document_amount=Decimal("1200.00"),
        document_type=DocumentType.INVOICE,
        vendor_name="Acme",
        risk_level=RiskLevel.LOW,
        initiated_by=uuid4(),
        initiated_at=datetime.now(UTC),
        auto_approved=False,
        auto_rejected=False,
        is_urgent=False,
        metadata={},
    )


def _steps(workflow: ApprovalWorkflow, count: int) -> list[ApprovalStep]:
    return [
        ApprovalStep(
            id=uuid4(),
            workflow_id=workflow.id,
            org_id=ORG,
            step_number=number,
            stage_number=number,
            step_name=f"Step {number}",
            approver_id=uuid4(),
            approver_role=OrgRole.APPROVER,
            created_at=datetime.now(UTC),
        )
        for number in range(1, count + 1)
    ]


@pytest.mark.parametrize("step_count", [1, 3, 6])
@pytest.mark.asyncio
async def test_start_workflow_inserts_steps_in_one_statement(step_count):
    workflow = _workflow(step_count)
    steps = _steps(workflow, step_count)

    step_repository = StepRepository()
    history_repository = HistoryRepository()

    engine = ApprovalEngine(
        WorkflowRepository(),
        step_repository,
        history_repository,
        audit_service=None,
    )

    created = await engine.start_workflow(workflow=workflow, steps=steps)

    assert created.id == workflow.id
    assert step_repository.batch_calls == 1
    assert step_repository.single_calls == 0
    assert len(step_repository.batch) == step_count
    assert steps[0].decision == ApprovalDecision.PENDING
    assert all(step.decision == ApprovalDecision.SKIPPED for step in steps[1:])
    assert history_repository.calls == 1

    # The history event refers to a real step, not a placeholder.
    assert steps[0].id is not None
