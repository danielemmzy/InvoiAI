"""The document approval timeline must batch steps and history.

Both satellite tables were previously queried once per workflow.
"""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.core.permissions import VIEW_APPROVALS

ORG = UUID("00000000-0000-0000-0000-0000000000dd")
DOC = UUID("00000000-0000-0000-0000-0000000000ee")


class Query:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs): return self
    def eq(self, *_args, **_kwargs): return self
    def order(self, *_args, **_kwargs): return self
    def limit(self, *_args, **_kwargs): return self
    def execute(self): return SimpleNamespace(data=self.rows)


class StepRepository:
    def __init__(self):
        self.calls = []

    async def list_steps_for_workflows(self, workflow_ids):
        self.calls.append(list(workflow_ids))
        return {
            str(workflow_id): [
                SimpleNamespace(
                    step_number=1,
                    model_dump=lambda mode="json", wid=workflow_id: {"workflow_id": str(wid)},
                )
            ]
            for workflow_id in workflow_ids
        }

    async def list_workflow_steps(self, _workflow_id):  # pragma: no cover - regression path
        raise AssertionError("steps must not be fetched per workflow")


class HistoryRepository:
    def __init__(self):
        self.calls = []

    async def list_workflow_history_for_workflows(self, workflow_ids):
        self.calls.append(list(workflow_ids))
        return {
            str(workflow_id): [
                SimpleNamespace(model_dump=lambda mode="json": {"event": "created"})
            ]
            for workflow_id in workflow_ids
        }

    async def list_workflow_history(self, _workflow_id):  # pragma: no cover - regression path
        raise AssertionError("history must not be fetched per workflow")


@pytest.mark.asyncio
async def test_document_approval_history_batches_satellite_queries(monkeypatch):
    import app.routers.approvals as approvals_module

    workflows = [
        {"id": str(uuid4()), "org_id": str(ORG), "document_id": str(DOC)}
        for _ in range(6)
    ]

    class Database:
        def table(self, _name):
            return Query(workflows)

    steps = StepRepository()
    history = HistoryRepository()
    container = SimpleNamespace(
        approval_workflow_repository=SimpleNamespace(),
        approval_step_repository=steps,
        approval_history_repository=history,
    )

    import app.core.supabase as supabase_module

    monkeypatch.setattr(supabase_module, "get_supabase", lambda: Database())
    monkeypatch.setattr(approvals_module, "get_container", lambda: container)

    ctx = SimpleNamespace(org_id=ORG, permissions={VIEW_APPROVALS})

    result = await approvals_module.get_document_approval_history(DOC, ctx)

    assert len(result) == 6
    assert len(steps.calls) == 1
    assert len(history.calls) == 1
    assert len(steps.calls[0]) == 6
    assert len(history.calls[0]) == 6
