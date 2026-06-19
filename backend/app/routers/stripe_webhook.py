import stripe
import logging
import asyncio
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

    logger.info("=" * 80)
    logger.info(f"EVENT TYPE = {event['type']}")
    logger.info("=" * 80)
    logger.info("WEBHOOK FILE VERSION 12345")

    # Route to the correct handler
    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("=" * 80)
    logger.info(f"STRIPE EVENT RECEIVED: {event_type}")
    logger.info(f"EVENT OBJECT ID: {data}")
    logger.info("=" * 80)

    if event_type == "checkout.session.completed":
        logger.info("ENTERING CHECKOUT SESSION HANDLER")

        try:
            await _handle_checkout_completed(data)
        except Exception as e:
            logger.exception(
                f"checkout.session.completed crashed: {e}"
            )
            raise

    elif event_type == "customer.subscription.updated":
        logger.info("CUSTOMER SUBSCRIPTION UPDATED")

        try:
            await _handle_subscription_updated(data)
        except Exception as e:
            logger.exception(
                f"customer.subscription.updated crashed: {e}"
            )
            raise

    elif event_type == "customer.subscription.deleted":
        logger.info("CUSTOMER SUBSCRIPTION DELETED")

        try:
            await _handle_subscription_deleted(data)
        except Exception as e:
            logger.exception(
                f"customer.subscription.deleted crashed: {e}"
            )
            raise

    elif event_type == "invoice.payment_failed":
        logger.info("INVOICE PAYMENT FAILED")

        try:
            await _handle_payment_failed(data)
        except Exception as e:
            logger.exception(
                f"invoice.payment_failed crashed: {e}"
            )
            raise

    elif event_type == "invoice.payment_succeeded":
        logger.info("INVOICE PAYMENT SUCCEEDED")

    else:
        logger.info(f"Unhandled Stripe event: {event_type}")

    return {"received": True}


async def _handle_checkout_completed(session: dict):
    """
    User completed checkout.
    Upgrade plan and create subscription record.
    """
    session = session.to_dict()

    logger.info("=" * 80)
    logger.info("CHECKOUT COMPLETED HANDLER STARTED")
    logger.info(f"SESSION ID: {session.get('id')}")
    logger.info(f"SESSION DATA: {session}")
    logger.info("=" * 80)

    supabase = get_supabase()

    customer_id = session.get("customer")
    client_reference_id = session.get("client_reference_id")
    subscription_id = session.get("subscription")

    logger.info(
        f"customer_id={customer_id} | "
        f"user_id={client_reference_id} | "
        f"subscription_id={subscription_id}"
    )

    if not client_reference_id:
        logger.error("client_reference_id missing from checkout session")
        return

    if not customer_id:
        logger.error("customer_id missing from checkout session")
        return

    if not subscription_id:
        logger.error("subscription_id missing from checkout session")
        return

    try:
        logger.info(f"Retrieving Stripe subscription: {subscription_id}")

        subscription = await asyncio.get_event_loop().run_in_executor(
    None, stripe.Subscription.retrieve, subscription_id
)
        subscription = subscription.to_dict()

        logger.info("ABOUT TO RETRIEVE SUBSCRIPTION")
        logger.info(f"SUBSCRIPTION ID = {subscription_id}")

        logger.info(f"SUBSCRIPTION RESPONSE: {subscription}")

        price_id = subscription["items"]["data"][0]["price"]["id"]

        logger.info(f"PRICE ID FROM STRIPE: {price_id}")
        logger.info(f"PRICE MAP: {PRICE_TO_PLAN}")

        plan = PRICE_TO_PLAN.get(price_id, "free")

        logger.info(f"MAPPED PLAN: {plan}")

        logger.info(
            f"Updating profile | "
            f"user={client_reference_id} | "
            f"customer={customer_id} | "
            f"plan={plan}"
        )

        profile_result = (
            supabase.table("profiles")
            .update({
                "stripe_customer_id": customer_id,
                "plan": plan,
            })
            .eq("id", client_reference_id)
            .execute()
        )

        logger.info(f"PROFILE UPDATE RESULT: {profile_result}")

        subscription_payload = {
            "user_id": client_reference_id,
            "stripe_subscription_id": subscription_id,
            "stripe_price_id": price_id,
            "plan": plan,
            "status": "active",
            "current_period_start": _ts(subscription["current_period_start"]),
            "current_period_end": _ts(subscription["current_period_end"]),
        }

        logger.info(
            f"UPSERTING SUBSCRIPTION RECORD: {subscription_payload}"
        )

        subscription_result = (
            supabase.table("subscriptions")
            .upsert(subscription_payload)
            .execute()
        )

        logger.info(
            f"SUBSCRIPTION UPSERT RESULT: {subscription_result}"
        )

        logger.info(
            f"SUCCESS: User {client_reference_id} upgraded to {plan}"
        )

    except Exception as e:
        logger.exception(
            f"CHECKOUT HANDLER FAILED FOR USER {client_reference_id}: {e}"
        )


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