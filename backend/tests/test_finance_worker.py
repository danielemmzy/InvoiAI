from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app2.core.enum.finance import OwnerType
from app2.workers.finance_worker import FinanceWorker


class FakeBudgetRepository:
    def __init__(self):
        self.created = []

    async def list_all_for_period(self, period_month):
        return [
            SimpleNamespace(
                owner_type=OwnerType.PERSONAL,
                owner_id=OWNER_ID,
                category="food",
                monthly_limit=Decimal("500"),
            )
        ]

    async def list_for_period(self, owner_type, owner_id, period_month):
        return []

    async def get_or_create_period(
        self,
        owner_type,
        owner_id,
        category,
        period_month,
        default_limit,
    ):
        self.created.append(
            (owner_type, owner_id, category, period_month, default_limit)
        )
        return SimpleNamespace(id=uuid4())


class FakeRecurringRepository:
    def __init__(self):
        self.item_id = uuid4()

    async def list_all_active(self):
        return [
            SimpleNamespace(
                id=self.item_id,
                owner_type=OwnerType.PERSONAL,
                owner_id=OWNER_ID,
                name="Internet",
                amount=Decimal("50"),
                next_due_date=date(2026, 8, 15),
            )
        ]


class FakeGoalRepository:
    def __init__(self):
        self.goal_id = uuid4()

    async def list_all_active(self):
        return [
            SimpleNamespace(
                id=self.goal_id,
                owner_type=OwnerType.PERSONAL,
                owner_id=OWNER_ID,
                name="Emergency fund",
                target_amount=Decimal("1000"),
                current_amount=Decimal("250"),
            )
        ]


class FakeNotificationRepository:
    def __init__(self):
        self.keys = set()

    async def exists_with_data_key(self, *, user_id, event_key):
        return event_key in self.keys


class FakeNotificationService:
    def __init__(self, repository):
        self.repository = repository
        self.sent = []

    async def send(self, **kwargs):
        self.repository.keys.add(kwargs["data"]["finance_event_key"])
        self.sent.append(kwargs)
        return SimpleNamespace(id=uuid4())


OWNER_ID = uuid4()


@pytest.mark.asyncio
async def test_monthly_budget_reset_is_idempotent():
    budgets = FakeBudgetRepository()
    notifications_repo = FakeNotificationRepository()
    notifications = FakeNotificationService(notifications_repo)

    worker = FinanceWorker(
        budget_repository=budgets,
        recurring_repository=SimpleNamespace(
            list_all_active=lambda: _async_empty()
        ),
        goal_repository=SimpleNamespace(
            list_all_active=lambda: _async_empty()
        ),
        notification_repository=notifications_repo,
        notification_service=notifications,
    )

    result = await worker._reset_monthly_budgets(date(2026, 8, 1))

    assert result == 1
    assert budgets.created[0][3] == date(2026, 8, 1)


@pytest.mark.asyncio
async def test_recurring_item_due_tomorrow_sends_once():
    notifications_repo = FakeNotificationRepository()
    notifications = FakeNotificationService(notifications_repo)
    recurring = FakeRecurringRepository()

    worker = FinanceWorker(
        budget_repository=SimpleNamespace(),
        recurring_repository=recurring,
        goal_repository=SimpleNamespace(),
        notification_repository=notifications_repo,
        notification_service=notifications,
    )

    first = await worker._notify_recurring_due_tomorrow(date(2026, 8, 14))
    second = await worker._notify_recurring_due_tomorrow(date(2026, 8, 14))

    assert first == 1
    assert second == 0


@pytest.mark.asyncio
async def test_goal_progress_is_monthly_idempotent():
    notifications_repo = FakeNotificationRepository()
    notifications = FakeNotificationService(notifications_repo)
    goals = FakeGoalRepository()

    worker = FinanceWorker(
        budget_repository=SimpleNamespace(),
        recurring_repository=SimpleNamespace(),
        goal_repository=goals,
        notification_repository=notifications_repo,
        notification_service=notifications,
    )

    first = await worker._notify_goal_progress(date(2026, 8, 14))
    second = await worker._notify_goal_progress(date(2026, 8, 14))

    assert first == 1
    assert second == 0
    assert "25.0%" in notifications.sent[0]["message"]


async def _async_empty():
    return []
