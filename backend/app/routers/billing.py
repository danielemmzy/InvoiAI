import stripe
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from app.core.config import settings
from app.core.auth import get_current_user, AuthUser
from app.core.limiter import limiter
from app.core.supabase import get_supabase
from app.services.usage import get_usage_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

stripe.api_key = settings.stripe_secret_key

# Maps plan name to Stripe price ID
# These come from your .env file
def get_price_id(plan: str) -> str:
    prices = {
        "starter": settings.stripe_price_starter,
        "pro": settings.stripe_price_pro,
    }
    return prices.get(plan, "")


class CheckoutRequest(BaseModel):
    plan: str          # "starter" or "pro"
    success_url: str   # where to send user after payment
    cancel_url: str    # where to send user if they cancel


@router.post("/checkout")
@limiter.limit("10/minute")
async def create_checkout_session(
    request: Request,
    body: CheckoutRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Creates a Stripe Checkout Session.

    Frontend calls this when user clicks "Upgrade".
    Returns a Stripe-hosted checkout URL.
    Frontend redirects user to that URL.
    After payment Stripe calls our webhook automatically.

    Requires: Authorization: Bearer <access_token>
    """
    if body.plan not in ("starter", "pro"):
        raise HTTPException(
            status_code=400,
            detail="Invalid plan. Choose 'starter' or 'pro'."
        )

    price_id = get_price_id(body.plan)
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail="Plan not configured. Contact support."
        )

    supabase = get_supabase()

    # Check if user already has a Stripe customer ID
    # If yes — use it so Stripe remembers their payment method
    try:
        profile = (
            supabase.table("profiles")
            .select("stripe_customer_id")
            .eq("id", current_user.id)
            .single()
            .execute()
        )
        customer_id = profile.data.get("stripe_customer_id") if profile.data else None
    except Exception:
        customer_id = None

    try:
        session_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": body.success_url,
            "cancel_url": body.cancel_url,

            # This is how we know WHICH USER paid
            # Stripe sends this back in the webhook
            "client_reference_id": current_user.id,

            # Pre-fill their email on the Stripe checkout page
            "customer_email": current_user.email if not customer_id else None,

            # Use existing customer if we have one
            "customer": customer_id if customer_id else None,

            # Collect billing address for tax purposes
            "billing_address_collection": "auto",
        }

        # Remove None values — Stripe doesn't like them
        session_params = {k: v for k, v in session_params.items() if v is not None}

        session = stripe.checkout.Session.create(**session_params)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout error for {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not create checkout session. Please try again."
        )

    logger.info(f"Checkout session created for {current_user.id} plan={body.plan}")

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }


@router.get("/subscription")
@limiter.limit("30/minute")
async def get_subscription(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Returns the user's current subscription details.
    Frontend uses this to show plan info and manage subscription.
    Requires: Authorization: Bearer <access_token>
    """
    supabase = get_supabase()

    # Get subscription record
    try:
        result = (
            supabase.table("subscriptions")
            .select("*")
            .eq("user_id", current_user.id)
            .single()
            .execute()
        )
        subscription = result.data
    except Exception:
        subscription = None

    # Get usage
    usage = await get_usage_summary(current_user.id, current_user.plan)

    return {
        "plan": current_user.plan,
        "usage": usage,
        "subscription": subscription,
    }


@router.post("/cancel")
@limiter.limit("5/minute")
async def cancel_subscription(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Cancels the user's subscription at period end.
    They keep access until the current billing period ends.
    Requires: Authorization: Bearer <access_token>
    """
    supabase = get_supabase()

    try:
        result = (
            supabase.table("subscriptions")
            .select("stripe_subscription_id")
            .eq("user_id", current_user.id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="No active subscription found")

    if not result.data:
        raise HTTPException(status_code=404, detail="No active subscription found")

    stripe_sub_id = result.data["stripe_subscription_id"]

    try:
        # cancel_at_period_end=True means they keep access until period ends
        # Not an immediate cancellation
        stripe.Subscription.modify(
            stripe_sub_id,
            cancel_at_period_end=True,
        )

        supabase.table("subscriptions").update(
            {"cancel_at_period_end": True}
        ).eq("stripe_subscription_id", stripe_sub_id).execute()

    except stripe.error.StripeError as e:
        logger.error(f"Cancel error for {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not cancel subscription. Please try again."
        )

    logger.info(f"Subscription set to cancel at period end for {current_user.id}")

    return {
        "message": "Subscription will cancel at end of current billing period. You keep full access until then."
    }