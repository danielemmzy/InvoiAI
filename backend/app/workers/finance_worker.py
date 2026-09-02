from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, timedelta
from typing import Iterable
from uuid import UUID

from app.core.enum.finance import OwnerType
from app.core.enum.notification import NotificationType
from app.repositories.finance.finance_repository import (
    BudgetRepository,
    GoalRepository,
    RecurringItemRepository,
)
from app.repositories.notification.notification_repository import (
    NotificationRepository,
)
from app.repositories.organization.member_repository import MemberRepository
from app.services.notification.notification_service import NotificationService
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class FinanceWorker(BaseWorker):
    """
    Scheduled personal-finance maintenance worker.

    Responsibilities
    ----------------
    1. On the first day of a month, materialize the new month's budget
       rows from the previous month's configured limits.
    2. Notify owners about active recurring items due tomorrow.
    3. Publish a monthly savings-goal progress update.

    This worker contains orchestration only. Finance calculations and
    persistence remain in repositories/services.

    The worker is intentionally idempotent:
    - budget periods are created through get_or_create_period()
    - notification events use deterministic finance_event_key values
      stored in notification.data
    """

    def __init__(
        self,
        *,
        budget_repository: BudgetRepository | None = None,
        recurring_repository: RecurringItemRepository | None = None,
        goal_repository: GoalRepository | None = None,
        notification_repository: NotificationRepository | None = None,
        member_repository: MemberRepository | None = None,
        notification_service: NotificationService,
    ) -> None:
        super().__init__()
        self.budgets = budget_repository or BudgetRepository()
        self.recurring = recurring_repository or RecurringItemRepository()
        self.goals = goal_repository or GoalRepository()
        self.notifications_repository = (
            notification_repository or NotificationRepository()
        )
        self.members = member_repository or MemberRepository()
        self.notifications = notification_service

    async def run(self) -> dict[str, int]:
        """
        Execute the daily finance maintenance cycle.

        The scheduler should invoke this once per day. Monthly work is
        guarded by the calendar date, so it is safe to run more often.
        """
        today = date.today()

        budget_rows = await self._reset_monthly_budgets(today)
        recurring = await self._notify_recurring_due_tomorrow(today)
        goals = await self._notify_goal_progress(today)

        return {
            "budget_periods_created": budget_rows,
            "recurring_reminders_sent": recurring,
            "goal_updates_sent": goals,
        }

    async def run_pending(self) -> dict[str, int]:
        """Scheduler-compatible entry point."""
        return await self.execute()

    async def _reset_monthly_budgets(self, today: date) -> int:
        if today.day != 1:
            return 0

        current_month = today.replace(day=1)
        previous_month = self._previous_month(current_month)

        previous_rows = await self.budgets.list_all_for_period(
            previous_month,
        )

        created = 0
        owners: set[tuple[OwnerType, UUID]] = set()

        for budget in previous_rows:
            owner_type = OwnerType(budget.owner_type)
            owner_id = UUID(str(budget.owner_id))
            owners.add((owner_type, owner_id))

            existing = await self.budgets.list_for_period(
                owner_type,
                owner_id,
                current_month,
            )

            existing_categories = {
                str(item.category.value if hasattr(item.category, "value") else item.category)
                for item in existing
            }

            category = (
                budget.category.value
                if hasattr(budget.category, "value")
                else str(budget.category)
            )

            if category in existing_categories:
                continue

            await self.budgets.get_or_create_period(
                owner_type,
                owner_id,
                category,
                current_month,
                budget.monthly_limit,
            )
            created += 1

        for owner_type, owner_id in owners:
            await self._notify_once(
                user_id=await self._notification_user_id(
                    owner_type,
                    owner_id,
                ),
                organization_id=(
                    owner_id
                    if owner_type == OwnerType.ORGANIZATION
                    else None
                ),
                event_type=NotificationType.FINANCE_BUDGET_RESET,
                title="New monthly budget started",
                message=(
                    f"Your {current_month.strftime('%B %Y')} budget "
                    "period is now active."
                ),
                event_key=(
                    f"budget-reset:{owner_type.value}:"
                    f"{owner_id}:{current_month.isoformat()}"
                ),
                data={
                    "period_month": current_month.isoformat(),
                },
            )

        return created

    async def _notify_recurring_due_tomorrow(
        self,
        today: date,
    ) -> int:
        tomorrow = today + timedelta(days=1)
        items = await self.recurring.list_all_active()

        sent = 0

        for item in items:
            if item.next_due_date != tomorrow:
                continue

            user_id = await self._notification_user_id(
                item.owner_type,
                item.owner_id,
            )

            event_key = (
                f"recurring-due:{item.id}:{tomorrow.isoformat()}"
            )

            if await self._notify_once(
                user_id=user_id,
                organization_id=(
                    item.owner_id
                    if item.owner_type == OwnerType.ORGANIZATION
                    else None
                ),
                event_type=NotificationType.FINANCE_RECURRING_DUE,
                title="Recurring payment due tomorrow",
                message=(
                    f"{item.name} is due tomorrow "
                    f"for {item.amount}."
                ),
                event_key=event_key,
                data={
                    "recurring_item_id": str(item.id),
                    "due_date": tomorrow.isoformat(),
                    "amount": str(item.amount),
                    "name": item.name,
                },
            ):
                sent += 1

        return sent

    async def _notify_goal_progress(self, today: date) -> int:
        goals = await self.goals.list_all_active()
        sent = 0

        for goal in goals:
            if goal.target_amount <= 0:
                continue

            # A monthly progress update avoids noisy daily notifications
            # while still giving the user a predictable progress cadence.
            event_key = (
                f"goal-progress:{goal.id}:"
                f"{today.year:04d}-{today.month:02d}"
            )

            percentage = min(
                100.0,
                float(
                    (goal.current_amount / goal.target_amount) * 100
                ),
            )

            user_id = await self._notification_user_id(
                goal.owner_type,
                goal.owner_id,
            )

            if await self._notify_once(
                user_id=user_id,
                organization_id=(
                    goal.owner_id
                    if goal.owner_type == OwnerType.ORGANIZATION
                    else None
                ),
                event_type=NotificationType.FINANCE_GOAL_PROGRESS,
                title=f"Savings goal: {goal.name}",
                message=(
                    f"You are {percentage:.1f}% toward your "
                    f"{goal.target_amount} savings goal."
                ),
                event_key=event_key,
                data={
                    "goal_id": str(goal.id),
                    "current_amount": str(goal.current_amount),
                    "target_amount": str(goal.target_amount),
                    "progress_percent": percentage,
                },
            ):
                sent += 1

        return sent

    async def _notify_once(
        self,
        *,
        user_id: UUID | None,
        organization_id: UUID | None,
        event_type: NotificationType,
        title: str,
        message: str,
        event_key: str,
        data: dict,
    ) -> bool:
        if user_id is None:
            logger.warning(
                "Skipping finance notification without recipient: %s",
                event_key,
            )
            return False

        if await self.notifications_repository.exists_with_data_key(
            user_id=user_id,
            event_key=event_key,
        ):
            return False

        payload = {
            **data,
            "finance_event_key": event_key,
        }

        result = await self.notifications.send(
            user_id=user_id,
            organization_id=organization_id,
            type=event_type,
            title=title,
            message=message,
            data=payload,
        )

        return result is not None

    async def _notification_user_id(
        self,
        owner_type: OwnerType,
        owner_id: UUID,
    ) -> UUID | None:
        if owner_type == OwnerType.PERSONAL:
            return owner_id

        owner = await self.members.get_owner(owner_id)

        if owner is None:
            logger.warning(
                "No active organization owner found for finance owner %s",
                owner_id,
            )
            return None

        return UUID(str(owner.user_id))

    @staticmethod
    def _previous_month(month: date) -> date:
        if month.month == 1:
            return month.replace(
                year=month.year - 1,
                month=12,
                day=1,
            )

        return month.replace(
            month=month.month - 1,
            day=1,
        )
