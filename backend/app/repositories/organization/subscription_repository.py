"""
============================================================
Subscription Repository

Persistence for subscriptions.

No business logic.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import (
    PlanType,
    SubscriptionStatus,
)
from app.mappers.subscription_mapper import (
    SubscriptionMapper,
)
from app.models.domain.subscription import (
    Subscription,
)
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository):
    """
    Repository for subscriptions.
    """

    table_name = "subscriptions"

    mapper = SubscriptionMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def create_subscription(
        self,
        subscription: Subscription | dict,
    ) -> Subscription | None:

        return await self.create(
            subscription,
        )

    async def get_subscription(
        self,
        subscription_id: UUID,
    ) -> Subscription | None:

        return await self.get(
            subscription_id,
        )

    async def update_subscription(
        self,
        subscription_id: UUID,
        data,
    ) -> Subscription | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(
                UTC,
            )

        return await self.update(
            subscription_id,
            data,
        )

    async def delete_subscription(
        self,
        subscription_id: UUID,
    ) -> bool:

        return await self.delete(
            subscription_id,
        )

    # =========================================================
    # Lookups
    # =========================================================

    async def get_by_org(
        self,
        org_id: UUID,
    ) -> Subscription | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def get_by_stripe_subscription(
        self,
        stripe_subscription_id: str,
    ) -> Subscription | None:

        response = (
            self.table()
            .select("*")
            .eq(
                "stripe_subscription_id",
                stripe_subscription_id,
            )
            .limit(1)
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Queries
    # =========================================================

    async def list_by_status(
        self,
        status: SubscriptionStatus,
    ) -> list[Subscription]:

        response = (
            self.table()
            .select("*")
            .eq("status", status.value)
            .order("created_at", desc=True)
            .execute()
        )

        return self._many(response)

    async def list_by_plan(
        self,
        plan: PlanType,
    ) -> list[Subscription]:

        response = (
            self.table()
            .select("*")
            .eq("plan", plan.value)
            .order("created_at", desc=True)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Subscription Actions
    # =========================================================

    async def update_status(
        self,
        subscription_id: UUID,
        status: SubscriptionStatus,
    ) -> Subscription | None:

        return await self.update_subscription(
            subscription_id,
            {
                "status": status.value,
            },
        )

    async def change_plan(
        self,
        subscription_id: UUID,
        plan: PlanType,
        document_limit: int,
    ) -> Subscription | None:

        return await self.update_subscription(
            subscription_id,
            {
                "plan": plan.value,
                "document_limit": document_limit,
            },
        )

    async def cancel_at_period_end(
        self,
        subscription_id: UUID,
        value: bool,
    ) -> Subscription | None:

        return await self.update_subscription(
            subscription_id,
            {
                "cancel_at_period_end": value,
            },
        )

    async def mark_cancelled(
        self,
        subscription_id: UUID,
    ) -> Subscription | None:

        return await self.update_subscription(
            subscription_id,
            {
                "status": SubscriptionStatus.CANCELED.value,
                "cancelled_at": datetime.now(UTC),
            },
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def subscription_exists(
        self,
        subscription_id: UUID,
    ) -> bool:

        return await self.exists(
            "id",
            subscription_id,
        )