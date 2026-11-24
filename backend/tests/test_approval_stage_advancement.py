"""Approval advancement must not scale round trips with the number of steps.

Advancing a stage used to read the workflow's steps three times and update
each withdrawing/activating step with its own statement.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.core.enum.database import ApprovalDecision
from app.repositories.approval.step_repository import ApprovalStepRepository
from app.services.approval.approval_engine import ApprovalEngine

ORG = UUID("00000000-0000-0000-0000-0000000000dd")


def _step(stage_number, step_number, decision):
    return SimpleNamespace(
        id=uuid4(),
        stage_number=stage_number,
        step_number=step_number,
        decision=decision,
    )


def _workflow(execution_mode):
    return SimpleNamespace(
        id=uuid4(),
        org_id=ORG,
        execution_mode=execution_mode,
    )


class CountingSteps:
    def __init__(self, steps):
        self.steps = steps
        self.list_calls = 0
        self.bulk_updates = []
        self.single_updates = []

    async def list_workflow_steps(self, _workflow_id):
        self.list_calls += 1
        return list(self.steps)

    async def update_steps(self, step_ids, data, *, org_id=None):
        self.bulk_updates.append(
            ([str(step_id) for step_id in step_ids], dict(data), org_id)
        )
        return [step for step in self.steps if step.id in set(step_ids)]

    async def update_step(self, step_id, data):  # pragma: no cover - regression path
        self.single_updates.append((step_id, data))
        raise AssertionError("advancement must not update steps one at a time")


class CountingWorkflows:
    def __init__(self):
        self.updates = []

    async def update_workflow(self, workflow_id, data):
        self.updates.append(dict(data))
        return SimpleNamespace(id=workflow_id)


@pytest.mark.asyncio
async def test_any_one_stage_withdraws_siblings_in_one_statement():
    completed = _step(1, 1, ApprovalDecision.APPROVED)
    siblings = [_step(1, number, ApprovalDecision.PENDING) for number in (2, 3, 4, 5)]
    next_stage = [_step(2, 6, ApprovalDecision.SKIPPED)]
    workflow = _workflow("any_one")

    steps = CountingSteps([completed, *siblings, *next_stage])
    workflows = CountingWorkflows()
    engine = ApprovalEngine.__new__(ApprovalEngine)
    engine.steps = steps
    engine.workflows = workflows
    engine.record_history = AsyncMock()
    engine._record_history = AsyncMock()

    await engine._advance_after_approval(
        workflow=workflow,
        completed_step=completed,
        actor_id=uuid4(),
    )

    # One read of the workflow's steps for the current stage, the last-stage
    # test and the next stage.
    assert steps.list_calls == 1
    # One bulk write to withdraw the siblings, one to activate the next stage.
    assert len(steps.bulk_updates) == 2
    withdrawn_ids, withdrawn_data, withdrawn_org = steps.bulk_updates[0]
    assert withdrawn_ids == [str(sibling.id) for sibling in siblings]
    assert withdrawn_data["decision"] == ApprovalDecision.SKIPPED.value
    activated_ids, activated_data, activated_org = steps.bulk_updates[1]
    assert activated_ids == [str(step.id) for step in next_stage]
    assert activated_data["decision"] == ApprovalDecision.PENDING.value
    # Both bulk writes stay inside the workflow's organization.
    assert withdrawn_org == workflow.org_id
    assert activated_org == workflow.org_id
    assert steps.single_updates == []
    assert workflows.updates[0]["current_stage"] == 2


@pytest.mark.asyncio
async def test_next_stage_activation_does_not_depend_on_step_count():
    completed = _step(1, 1, ApprovalDecision.APPROVED)
    next_stage = [
        _step(2, number, ApprovalDecision.SKIPPED) for number in (2, 3, 4, 5, 6)
    ]
    workflow = _workflow("sequential")

    steps = CountingSteps([completed, *next_stage])
    engine = ApprovalEngine.__new__(ApprovalEngine)
    engine.steps = steps
    engine.workflows = CountingWorkflows()
    engine._record_history = AsyncMock()

    await engine._advance_after_approval(
        workflow=workflow,
        completed_step=completed,
        actor_id=uuid4(),
    )

    assert steps.list_calls == 1
    assert len(steps.bulk_updates) == 1
    activated_ids, _, activated_org = steps.bulk_updates[0]
    assert len(activated_ids) == 5
    assert activated_org == workflow.org_id
    assert steps.single_updates == []


class RecordedQuery:
    def __init__(self, executed, table_name):
        self.executed = executed
        self.table_name = table_name
        self.filters = []
        self.updated_ids = None
        self.payload = None

    def update(self, payload):
        self.payload = payload
        return self

    def in_(self, column, values):
        self.filters.append((column, list(values)))
        self.updated_ids = list(values)
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def execute(self):
        self.executed.append((self.table_name, "update", self.updated_ids, list(self.filters)))
        now = datetime.now(UTC).isoformat()
        return SimpleNamespace(
            data=[
                {
                    "id": step_id,
                    "workflow_id": str(uuid4()),
                    "org_id": str(ORG),
                    "step_number": 1,
                    "stage_number": 1,
                    "step_name": "Step",
                    "approver_role": "admin",
                    "created_at": now,
                    **self.payload,
                }
                for step_id in self.updated_ids or []
            ]
        )


class RecordedDatabase:
    def __init__(self):
        self.executed = []

    def table(self, name):
        return RecordedQuery(self.executed, name)


@pytest.mark.asyncio
async def test_update_steps_issues_one_update_for_all_ids():
    database = RecordedDatabase()
    repository = object.__new__(ApprovalStepRepository)
    repository.db = database
    step_ids = [uuid4() for _ in range(6)]

    updated = await repository.update_steps(
        step_ids, {"decision": ApprovalDecision.SKIPPED.value}
    )

    assert len(database.executed) == 1
    table_name, operation, filters, where = database.executed[0]
    assert table_name == "approval_steps"
    assert operation == "update"
    assert filters == [str(step_id) for step_id in step_ids]
    # No tenant guard unless the caller supplies one.
    assert where == [("id", [str(step_id) for step_id in step_ids])]
    assert len(updated) == 6


@pytest.mark.asyncio
async def test_update_steps_filters_on_org_when_supplied():
    database = RecordedDatabase()
    repository = object.__new__(ApprovalStepRepository)
    repository.db = database
    step_ids = [uuid4() for _ in range(3)]

    await repository.update_steps(
        step_ids,
        {"decision": ApprovalDecision.SKIPPED.value},
        org_id=ORG,
    )

    assert len(database.executed) == 1
    _, _, updated_ids, where = database.executed[0]
    assert updated_ids == [str(step_id) for step_id in step_ids]
    # The tenant guard is part of the same single statement, not a second query.
    assert ("org_id", str(ORG)) in where
