from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.enum.database import PlanType, SubscriptionStatus
from app.core.plan import document_limit_for
from app.models.domain.subscription import Subscription
from app.repositories.billing.stripe_event_repository import StripeEventRepository
from app.repositories.organization.organization_repository import OrganizationRepository
from app.repositories.organization.subscription_repository import SubscriptionRepository

logger = logging.getLogger(__name__)


class StripeEventProcessor:
    """Idempotent Stripe billing event processor."""

    def __init__(
        self,
        *,
        events: StripeEventRepository,
        organizations: OrganizationRepository,
        subscriptions: SubscriptionRepository,
    ) -> None:
        self.events = events
        self.organizations = organizations
        self.subscriptions = subscriptions

    async def process(self, event: dict[str, Any]) -> bool:
        event_id = event.get("event_id") or event.get("id")
        event_type = event.get("event_type") or event.get("type")
        payload = event.get("object") or event.get("data", {}).get("object", {})

        if not event_id or not event_type:
            raise ValueError("Stripe event is missing id or type")

        existing = await self.events.get_by_stripe_event_id(event_id)
        if existing:
            if existing.status == "processed":
                return False
            if existing.status == "processing":
                logger.info("Ignoring concurrently processing Stripe event %s", event_id)
                return False
            await self.events.mark_processing(existing.id)
            event_record_id = existing.id
        else:
            try:
                created = await self.events.create_event(
                    stripe_event_id=event_id,
                    event_type=event_type,
                    payload=event,
                )
                if created is None:
                    raise RuntimeError("Stripe event could not be persisted")
                event_record_id = created.id
            except Exception:
                # A concurrent webhook may have won the unique stripe_event_id insert.
                existing = await self.events.get_by_stripe_event_id(event_id)
                if not existing:
                    raise
                if existing.status == "processed" or existing.status == "processing":
                    return False
                if not await self.events.mark_processing(existing.id):
                    return False
                event_record_id = existing.id

        try:
            await self._dispatch(event_type=event_type, payload=payload)
            await self.events.mark_processed(event_record_id)
            return True
        except Exception as exc:
            await self.events.mark_failed(event_record_id, str(exc))
            logger.exception("Stripe event %s failed", event_id)
            raise

    async def _dispatch(self, *, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "checkout.session.completed":
            await self._checkout_completed(payload)
        elif event_type == "customer.subscription.updated":
            await self._subscription_updated(payload)
        elif event_type == "customer.subscription.deleted":
            await self._subscription_deleted(payload)
        elif event_type == "invoice.payment_failed":
            await self._payment_failed(payload)
        else:
            logger.info("Ignoring unsupported Stripe event type %s", event_type)

    async def _resolve_org_id(self, payload: dict[str, Any]) -> UUID | None:
        metadata = payload.get("metadata") or {}
        org_id = metadata.get("org_id")
        if org_id:
            return UUID(str(org_id))

        customer_id = payload.get("customer")
        if customer_id:
            organization = await self.organizations.get_by_stripe_customer(customer_id)
            return organization.id if organization else None
        return None

    def _plan_from_price(self, price_id: str | None) -> PlanType:
        if not price_id:
            raise ValueError("Unknown Stripe price: None")
        price_map = {
            settings.stripe_price_starter: PlanType.STARTER,
            settings.stripe_price_starter_annual: PlanType.STARTER,
            settings.stripe_price_pro: PlanType.PRO,
            settings.stripe_price_pro_annual: PlanType.PRO,
            settings.stripe_price_business: PlanType.BUSINESS,
            settings.stripe_price_business_annual: PlanType.BUSINESS,
        }
        # Empty-string settings would otherwise collide as a shared "" key.
        price_map.pop("", None)
        plan = price_map.get(price_id)
        if plan is None:
            raise ValueError(f"Unknown Stripe price: {price_id}")
        return plan

    @staticmethod
    def _document_limit(plan: PlanType, current: int | None = None) -> int:
        # Preserve an explicitly configured organization limit; plan changes should
        # not silently overwrite a custom limit configured by an administrator.
        if current is not None:
            return current
        return document_limit_for(plan)

    async def _checkout_completed(self, payload: dict[str, Any]) -> None:
        org_id = await self._resolve_org_id(payload)
        if org_id is None:
            raise ValueError("Unable to resolve organization for checkout session")

        subscription_id = payload.get("subscription")
        customer_id = payload.get("customer")
        if not subscription_id:
            raise ValueError("Checkout session has no Stripe subscription")

        import stripe
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        await self._sync_subscription(org_id, stripe_subscription)
        if customer_id:
            await self.organizations.update_organization(
                org_id,
                {"stripe_customer_id": customer_id},
            )

    async def _subscription_updated(self, payload: dict[str, Any]) -> None:
        org_id = await self._resolve_org_id(payload)
        if org_id is None:
            subscription = await self.subscriptions.get_by_stripe_subscription(payload.get("id", ""))
            org_id = subscription.org_id if subscription else None
        if org_id is None:
            raise ValueError("Unable to resolve organization for subscription update")
        await self._sync_subscription(org_id, payload)

    async def _sync_subscription(self, org_id: UUID, payload: dict[str, Any]) -> None:
        price = (payload.get("items", {}).get("data") or [{}])[0].get("price") or {}
        price_id = price.get("id")
        plan = self._plan_from_price(price_id)
        status = SubscriptionStatus(str(payload.get("status", "active")))

        existing = await self.subscriptions.get_by_org(org_id)
        data = {
            "org_id": org_id,
            "stripe_subscription_id": payload.get("id"),
            "stripe_price_id": price_id,
            "stripe_product_id": price.get("product"),
            "plan": plan.value,
            "status": status.value,
            "cancel_at_period_end": bool(payload.get("cancel_at_period_end", False)),
            "trial_start": self._timestamp(payload.get("trial_start")),
            "trial_end": self._timestamp(payload.get("trial_end")),
            "current_period_start": self._timestamp(payload.get("current_period_start")),
            "current_period_end": self._timestamp(payload.get("current_period_end")),
            "cancelled_at": self._timestamp(payload.get("canceled_at")),
            "document_limit": self._document_limit(plan, existing.document_limit if existing else None),
            "metadata": payload.get("metadata") or {},
        }
        if existing:
            await self.subscriptions.update_subscription(existing.id, data)
        else:
            await self.subscriptions.create_subscription(data)
        await self.organizations.update_plan(org_id, plan)

    async def _subscription_deleted(self, payload: dict[str, Any]) -> None:
        subscription = await self.subscriptions.get_by_stripe_subscription(payload.get("id", ""))
        org_id = subscription.org_id if subscription else await self._resolve_org_id(payload)
        if org_id is None:
            raise ValueError("Unable to resolve organization for deleted subscription")
        if subscription:
            await self.subscriptions.mark_cancelled(subscription.id)
        await self.organizations.update_plan(org_id, PlanType.FREE)

    async def _payment_failed(self, payload: dict[str, Any]) -> None:
        subscription_id = payload.get("subscription")
        if not subscription_id:
            return
        subscription = await self.subscriptions.get_by_stripe_subscription(subscription_id)
        if subscription:
            await self.subscriptions.update_status(subscription.id, SubscriptionStatus.PAST_DUE)

    @staticmethod
    def _timestamp(value: Any):
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), tz=UTC)
