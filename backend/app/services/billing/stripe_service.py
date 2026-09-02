from __future__ import annotations
import stripe
from app.core.config import settings
from app.repositories.organization.subscription_repository import SubscriptionRepository

class StripeBillingService:
    def __init__(self, subscriptions: SubscriptionRepository | None = None):
        self.subscriptions = subscriptions or SubscriptionRepository()
        stripe.api_key = settings.stripe_secret_key
    async def checkout(self, *, user, org_id, plan, success_url, cancel_url, annual=False):
        price_map = {
            "starter": settings.stripe_price_starter_annual if annual else settings.stripe_price_starter,
            "pro": settings.stripe_price_pro_annual if annual else settings.stripe_price_pro,
            "business": settings.stripe_price_business_annual if annual else settings.stripe_price_business,
        }
        price_id = price_map.get(plan)
        if not price_id: raise ValueError("Plan not configured")
        session=stripe.checkout.Session.create(mode="subscription",line_items=[{"price":price_id,"quantity":1}],success_url=success_url,cancel_url=cancel_url,client_reference_id=str(user.id),customer_email=user.email,billing_address_collection="auto",metadata={"org_id": str(org_id)},subscription_data={"metadata": {"org_id": str(org_id)}})
        return {"checkout_url":session.url,"session_id":session.id}
    async def subscription(self,org_id): return await self.subscriptions.get_by_org(org_id)
    async def cancel(self,org_id):
        sub=await self.subscriptions.get_by_org(org_id)
        if not sub or not sub.stripe_subscription_id: raise ValueError("No active subscription found")
        stripe.Subscription.modify(sub.stripe_subscription_id,cancel_at_period_end=True)
        return await self.subscriptions.update_subscription(sub.id,{"cancel_at_period_end":True})
