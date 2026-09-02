"""
============================================================
Billing Service

Business logic for subscriptions.

Responsibilities
----------------
- Subscription retrieval
- Plan upgrades
- Plan downgrades
- Subscription cancellation
- Stripe synchronization

Repository handles persistence.

Stripe client handles API calls.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.core.enum.database import (
    PlanType,
    SubscriptionStatus,
)
from app.models.domain.subscription import Subscription
from app.repositories.organization.subscription_repository import (
    SubscriptionRepository,
)
from app.schemas.subscription import (
    SubscriptionUpdate,
)


class BillingService:
    """
    Billing business logic.
    """

    def __init__(
        self,
        repository: SubscriptionRepository,
    ):
        self.repository = repository

    # =========================================================
    # Retrieve
    # =========================================================

    async def get_subscription(
        self,
        subscription_id: UUID,
    ) -> Subscription | None:

        return await self.repository.get_subscription(
            subscription_id,
        )

    async def get_organization_subscription(
        self,
        org_id: UUID,
    ) -> Subscription | None:

        return await self.repository.get_by_org(
            org_id,
        )

    # =========================================================
    # Update
    # =========================================================

    async def update_subscription(
        self,
        subscription_id: UUID,
        update: SubscriptionUpdate,
    ) -> Subscription:

        subscription = await self.repository.get_subscription(
            subscription_id,
        )

        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )

        data = update.model_dump(
            exclude_unset=True,
        )

        return await self.repository.update_subscription(
            subscription_id,
            data,
        )
        # =========================================================
    # Plan Management
    # =========================================================

    async def change_plan(
        self,
        subscription_id: UUID,
        plan: PlanType,
        document_limit: int,
    ) -> Subscription:

        subscription = await self.repository.get_subscription(
            subscription_id,
        )

        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )

        return await self.repository.change_plan(
            subscription_id,
            plan,
            document_limit,
        )

    async def upgrade_plan(
        self,
        subscription_id: UUID,
        plan: PlanType,
        document_limit: int,
    ) -> Subscription:
        """
        Upgrade subscription plan.
        """

        subscription = await self.repository.get_subscription(
            subscription_id,
        )

        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )

        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ValueError(
                "Cannot upgrade a cancelled subscription."
            )

        return await self.repository.change_plan(
            subscription_id,
            plan,
            document_limit,
        )

    async def downgrade_plan(
        self,
        subscription_id: UUID,
        plan: PlanType,
        document_limit: int,
    ) -> Subscription:
        """
        Downgrade subscription plan.
        """

        subscription = await self.repository.get_subscription(
            subscription_id,
        )

        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )

        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ValueError(
                "Cannot downgrade a cancelled subscription."
            )

        return await self.repository.change_plan(
            subscription_id,
            plan,
            document_limit,
        )

        # =========================================================
    # Subscription Status
    # =========================================================

    async def cancel_subscription(
        self,
        subscription_id: UUID,
    ) -> Subscription:
        """
        Cancel a subscription.
        """

        subscription = await self.repository.get_subscription(
            subscription_id,
        )

        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )

        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ValueError(
                "Subscription is already cancelled."
            )

        return await self.repository.cancel_subscription(
            subscription_id,
        )

    async def reactivate_subscription(
        self,
        subscription_id: UUID,
    ) -> Subscription:
        """
        Reactivate a cancelled subscription.
        """

        subscription = await self.repository.get_subscription(
            subscription_id,
        )

        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )

        if subscription.status != SubscriptionStatus.CANCELLED:
            raise ValueError(
                "Subscription is not cancelled."
            )

        return await self.repository.update_status(
            subscription_id,
            SubscriptionStatus.ACTIVE,
        )

    async def update_status(
        self,
        subscription_id: UUID,
        status: SubscriptionStatus,
    ) -> Subscription:
        """
        Update subscription status.
        """

        subscription = await self.repository.get_subscription(
            subscription_id,
        )

        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )

        return await self.repository.update_status(
            subscription_id,
            status,
        )
        # =========================================================
    # Stripe Synchronization
    # =========================================================

    async def sync_subscription(
        self,
        subscription: Subscription,
    ) -> Subscription:
        """
        Synchronize subscription received from Stripe.
        """

        existing = await self.repository.get_by_org(
            subscription.org_id,
        )

        if existing is None:
            return await self.repository.create_subscription(
                subscription,
            )

        return await self.repository.update_subscription(
            existing.id,
            subscription.model_dump(
                exclude={
                    "id",
                    "created_at",
                    "updated_at",
                },
            ),
        )

    # =========================================================
    # Trial Helpers
    # =========================================================

    async def is_trial_active(
        self,
        org_id: UUID,
    ) -> bool:

        subscription = await self.repository.get_by_org(
            org_id,
        )

        if subscription is None:
            return False

        return (
            subscription.status
            == SubscriptionStatus.TRIALING
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def has_active_subscription(
        self,
        org_id: UUID,
    ) -> bool:

        subscription = await self.repository.get_by_org(
            org_id,
        )

        if subscription is None:
            return False

        return subscription.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        )

    async def current_plan(
        self,
        org_id: UUID,
    ) -> PlanType | None:

        subscription = await self.repository.get_by_org(
            org_id,
        )

        if subscription is None:
            return None

        return subscription.plan