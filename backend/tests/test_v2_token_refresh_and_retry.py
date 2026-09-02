from unittest.mock import AsyncMock
import pytest
from types import SimpleNamespace
from uuid import uuid4

from app2.workers.token_refresh_worker import TokenRefreshWorker
from app2.workers.base import BaseWorker


@pytest.mark.asyncio
async def test_token_refresh_deactivates_after_fourth_failure():
    conn = SimpleNamespace(
        id=uuid4(), org_id=uuid4(), provider=SimpleNamespace(value="quickbooks"),
        error_count=3,
    )
    repo = SimpleNamespace(
        list_active_connections=AsyncMock(return_value=[]),
        record_error=AsyncMock(),
        deactivate_connection=AsyncMock(),
        clear_error=AsyncMock(),
    )
    members = SimpleNamespace(get_owner=AsyncMock(return_value=None))
    notifications = SimpleNamespace(send=AsyncMock())

    worker = TokenRefreshWorker(
        connection_repository=repo,
        member_repository=members,
        notification_service=notifications,
        quickbooks_oauth=SimpleNamespace(),
        xero_oauth=SimpleNamespace(),
        token_service=SimpleNamespace(),
    )

    deactivated = await worker._record_failure(conn, RuntimeError("invalid_grant"))

    assert deactivated is True
    repo.record_error.assert_awaited_once_with(conn.id, "invalid_grant", 4)
    repo.deactivate_connection.assert_awaited_once_with(conn.id)


@pytest.mark.asyncio
async def test_base_worker_retries_and_returns_after_transient_failure(monkeypatch):
    class Worker(BaseWorker):
        def __init__(self):
            super().__init__(retries=3, retry_delay=0)
            self.calls = 0
        async def run(self, **kwargs):
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("transient")
            return {"ok": True}

    worker = Worker()
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("app.workers.base.asyncio.sleep", fake_sleep)

    result = await worker.execute()
    assert result == {"ok": True}
    assert worker.calls == 3
    assert sleeps == [0, 0]
