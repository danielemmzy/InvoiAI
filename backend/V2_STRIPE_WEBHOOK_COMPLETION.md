# V2 Stripe Webhook Completion

## Implemented

- Durable `stripe_events` persistence boundary.
- Unique Stripe event ID idempotency.
- Processing / processed / failed lifecycle.
- Retry of previously failed events.
- `checkout.session.completed` synchronization.
- `customer.subscription.updated` plan/status synchronization.
- `customer.subscription.deleted` downgrade to `free`.
- `invoice.payment_failed` transition to `past_due`.
- Organization resolution through checkout/subscription metadata or Stripe customer ID.
- Stripe customer ID persisted on checkout completion.
- Checkout sessions now carry `org_id` metadata on both the Checkout Session and Stripe Subscription.
- V2 webhook route: `POST /api/v2/webhooks/stripe`.
- Supabase migration: `migrations/20260816_stripe_idempotency.sql`.
- Targeted Stripe processor tests: **5 passed**.

## Verification

Targeted command:

```text
pytest tests/test_v2_stripe_webhook.py -q
5 passed
```

Python compilation:

```text
python -m compileall -q app tests
```

The complete suite was not claimed as passing in this environment because the execution environment could not install the project's pinned external dependencies (network/package-index access is unavailable). The existing suite also requires packages such as OpenAI and Google Document AI for collection.

## Production verification

After installing `requirements.txt` locally and configuring Supabase/Stripe test credentials:

```text
pytest tests/ -v --tb=short
```

Then send Stripe test-mode events to:

```text
POST /api/v2/webhooks/stripe
```

Verify `stripe_events` contains exactly one row per Stripe event ID and that the organization's plan/subscription state changes exactly once.
