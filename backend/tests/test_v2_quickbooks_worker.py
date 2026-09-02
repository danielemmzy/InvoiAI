import pytest
from types import SimpleNamespace
from uuid import uuid4

from app2.workers.quickbooks_worker import QuickBooksWorker


@pytest.mark.asyncio
async def test_quickbooks_worker_syncs_each_active_connection_once():
    connections = [
        SimpleNamespace(id=uuid4(), org_id=uuid4(), realm_id="r1"),
        SimpleNamespace(id=uuid4(), org_id=uuid4(), realm_id="r2"),
    ]

    class Repo:
        async def list_active_connections(self, provider):
            return connections

    calls = []
    class Sync:
        def __init__(self, **kwargs):
            calls.append(kwargs)
        async def sync(self):
            return {"invoices": 2}

    worker = QuickBooksWorker(
        sync_service_factory=Sync,
        integration_repository=Repo(),
    )

    result = await worker.run_pending(limit=50)

    assert result == {"processed": 2, "failed": 0}
    assert calls == [
        {"org_id": connections[0].org_id, "realm_id": "r1"},
        {"org_id": connections[1].org_id, "realm_id": "r2"},
    ]
