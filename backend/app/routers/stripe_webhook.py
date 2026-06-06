import stripe
import logging
from fastapi import APIRouter, Request, HTTPException
from app.core.config import settings
from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["Stripe"])

stripe.api_key = settings.stripe_secret_key

# Map Stripe price IDs to our plan names
# Add your actual Stripe price IDs in .env
PRICE_TO_PLAN = {
    settings.stripe_price_starter: "starter",
    settings.stripe_price_pro: "pro",
}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Receives events from Stripe and updates user plans accordingly.

    This is the ONLY place plan changes happen.
    Stripe calls this URL when:
      - User subscribes (checkout.session.completed)
      - Subscription renews (invoice.payment_succeeded)
      - Payment fails (invoice.payment_failed)
      - User cancels (customer.subscription.deleted)
      - User upgrades/downgrades (customer.subscription.updated)

    Security:
      Stripe signs every webhook with your STRIPE_WEBHOOK_SECRET.
      We verify this signature before processing ANYTHING.
      Without this check anyone could POST fake events and upgrade their plan.

    Setup in Stripe Dashboard:
      Developers → Webhooks → Add endpoint
      URL: https://yourdomain.com/stripe/webhook
      Events to listen for:
        - checkout.session.completed
        - customer.subscription.updated
        - customer.subscription.deleted
        - invoice.payment_succeeded
        - invoice.payment_failed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature — reject anything that doesn't match
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Webhook parse error: {e}")
        raise HTTPException(status_code=400, detail="Webhook error")

    logger.info(f"Stripe webhook received: {event['type']}")

    # Route to the correct handler
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)

    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data)

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data)

    # Always return 200 to Stripe — even for unhandled events
    # If we return 4xx Stripe will retry the webhook repeatedly
    return {"received": True}


async def _handle_checkout_completed(session: dict):
    """
    User completed the Stripe checkout.
    Link their Stripe customer ID to their profile
    and upgrade their plan.
    """
    supabase = get_supabase()

    customer_id = session.get("customer")
    client_reference_id = session.get("client_reference_id")  # our user_id
    subscription_id = session.get("subscription")

    if not client_reference_id or not customer_id:
        logger.warning("Checkout session missing user reference")
        return

    # Get subscription details to find the plan
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        price_id = subscription["items"]["data"][0]["price"]["id"]
        plan = PRICE_TO_PLAN.get(price_id, "free")

        # Save stripe_customer_id to profiles
        supabase.table("profiles").update({
            "stripe_customer_id": customer_id,
            "plan": plan,
        }).eq("id", client_reference_id).execute()

        # Create subscription record
        supabase.table("subscriptions").upsert({
            "user_id": client_reference_id,
            "stripe_subscription_id": subscription_id,
            "stripe_price_id": price_id,
            "plan": plan,
            "status": "active",
            "current_period_start": _ts(subscription["current_period_start"]),
            "current_period_end": _ts(subscription["current_period_end"]),
        }).execute()

        logger.info(f"User {client_reference_id} upgraded to {plan}")

    except Exception as e:
        logger.error(f"Checkout handler error: {e}")


async def _handle_subscription_updated(subscription: dict):
    """
    Plan changed — upgrade or downgrade.
    Update plan in both profiles and subscriptions tables.
    """
    supabase = get_supabase()

    subscription_id = subscription["id"]
    price_id = subscription["items"]["data"][0]["price"]["id"]
    plan = PRICE_TO_PLAN.get(price_id, "free")
    status = subscription["status"]  # active, past_due, trialing etc.

    try:
        # Find user by stripe subscription ID
        result = (
            supabase.table("subscriptions")
            .select("user_id")
            .eq("stripe_subscription_id", subscription_id)
            .single()
            .execute()
        )

        if not result.data:
            logger.warning(f"No user found for subscription {subscription_id}")
            return

        user_id = result.data["user_id"]

        # Update plan in profiles
        supabase.table("profiles").update({"plan": plan}).eq("id", user_id).execute()

        # Update subscription record
        supabase.table("subscriptions").update({
            "plan": plan,
            "stripe_price_id": price_id,
            "status": status,
            "current_period_start": _ts(subscription["current_period_start"]),
            "current_period_end": _ts(subscription["current_period_end"]),
            "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
        }).eq("stripe_subscription_id", subscription_id).execute()

        logger.info(f"User {user_id} plan updated to {plan} (status={status})")

    except Exception as e:
        logger.error(f"Subscription update handler error: {e}")


async def _handle_subscription_deleted(subscription: dict):
    """
    User cancelled and subscription period ended.
    Downgrade to free plan.
    """
    supabase = get_supabase()
    subscription_id = subscription["id"]

    try:
        result = (
            supabase.table("subscriptions")
            .select("user_id")
            .eq("stripe_subscription_id", subscription_id)
            .single()
            .execute()
        )

        if not result.data:
            return

        user_id = result.data["user_id"]

        # Downgrade to free
        supabase.table("profiles").update({"plan": "free"}).eq("id", user_id).execute()
        supabase.table("subscriptions").update(
            {"status": "cancelled"}
        ).eq("stripe_subscription_id", subscription_id).execute()

        logger.info(f"User {user_id} downgraded to free (subscription cancelled)")

    except Exception as e:
        logger.error(f"Subscription deletion handler error: {e}")


async def _handle_payment_failed(invoice: dict):
    """
    Payment failed — mark subscription as past_due.
    User keeps access until Stripe gives up retrying
    then subscription.deleted fires and we downgrade.
    """
    supabase = get_supabase()
    subscription_id = invoice.get("subscription")

    if not subscription_id:
        return

    try:
        supabase.table("subscriptions").update(
            {"status": "past_due"}
        ).eq("stripe_subscription_id", subscription_id).execute()

        logger.warning(f"Payment failed for subscription {subscription_id}")

    except Exception as e:
        logger.error(f"Payment failed handler error: {e}")


def _ts(unix_timestamp: int) -> str:
    """Converts Unix timestamp to ISO string for Postgres."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).isoformat()