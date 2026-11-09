# Operator runbooks

Owner: configure `ALERT_OWNER` to the named production responder before pilot.
The code default (`Platform on-call`) is a placeholder, not an assigned person
or team. Alerts are emitted through `app/services/observability/alerts.py`; when
`ALERT_WEBHOOK_URL` is unset they are logged only. Production alert delivery is
an external deployment gate until a real endpoint is configured and tested.

## Signals

| Signal | Source | First response |
|---|---|---|
| `api_requests_total`, `api_request_duration_ms`, `api_errors_total` | request middleware | Check latency/error spike by route |
| `provider_sync_total{provider,result}` | bill sync worker | Open provider outage runbook |
| `extraction_total{result}` | extraction/OCR pipeline | Open stuck workers runbook |
| `webhook_total{provider,result}` | webhook handlers | Open webhook replay runbook |
| `notification_delivery_total{channel,result}` | notification worker | Check provider status and retry queue |
| `queue_age_seconds{queue}` | worker schedulers | Open stuck workers runbook |
| `billing_seats{plan}`, `billing_allowance{plan,trial}` | billing service | Check plan/trial state |
| `quota_state_total{state}` | quota checks | Open quota runbook |

`GET /api/v2/ops/metrics` returns the in-process snapshot. It requires an
organization member with `audit:view`. Do not expose it publicly. Counters and
gauges live only in the current process and reset on restart; they are not a
durable or cross-worker monitoring backend. Configure a collector before using
them for production alert thresholds.

`POST /api/v2/ops/alerts/test` sends a test alert. Delivery requires
`ALERT_WEBHOOK_URL`; without it the response is
`{"delivered": false, "reason": "alert_webhook_not_configured"}`.
The endpoint proves delivery only to the configured webhook receiver; local
tests with a mocked transport do not prove a production alert was delivered.

## API latency and errors

1. Compare `api_request_duration_ms` and `api_errors_total` by route template.
2. Check `X-Request-ID` in application logs and follow the same ID through the
   request path. Do not use raw URLs, request bodies, or customer data in alert
   labels.
3. If metrics are unavailable after restart, confirm the collector is wired;
   the built-in registry is process-local.

## Stuck workers

1. Read `queue_age_seconds` and the worker's last structured log line.
2. Check the worker lease/claim row. A stale `sync_started_at`/`processing`
   state is recoverable through the existing recovery service.
3. Do not delete or rewrite an approved document to unstick a job. Requeue
   with the retry endpoint.
4. If the provider accepted a write but the local confirmation is missing,
   reconcile before retrying. A timeout is not proof of failure.

## Provider outage

1. Identify the provider from `provider_sync_total{provider="..."}`.
2. Check the provider status page and the connection health.
3. 401/403: ask the customer to reconnect. 429: honor `Retry-After`.
   5xx/timeout: bounded retry. 4xx validation: stop and show the safe reason.
4. Manual AP remains available while sync is down. Never fabricate a synced
   state.

## Webhook replay

1. Confirm the webhook signature before replaying. Unsigned routes stay closed.
2. Replay one event at a time and keep the provider event id deduplicated.
3. Record the replay in the audit log; never include the raw payload or token.
4. If the route is disabled by design (for example the payment webhook), keep
   it disabled until a signature-verifying adapter exists.

## Backup restore

1. Restore into a separate project/database first, never over production.
2. Verify counts and checksums for documents, approvals, and audit rows.
3. Verify that a sample private object can be signed and downloaded.
4. Only then schedule a cutover window with the owner.
5. Record the restore in the evidence log. Local evidence cannot prove the
   provider-side backup; mark it external until performed.

## Customer data deletion

1. Confirm the requester has authority for the organization.
2. Do not delete rows referenced by an open approval, open payment
   instruction, or the audit trail. Anonymize where policy allows.
3. Delete private objects only after the database reference is resolved.
4. Record the request, scope, and completion in the audit log.

## Secret rotation

1. Rotate one secret at a time; keep the previous value until the new one is
   verified.
2. OAuth client secrets, `TOKEN_ENCRYPTION_KEY`, provider webhook secrets, and
   SMTP credentials are server-side only. Never print them.
3. Rotating `TOKEN_ENCRYPTION_KEY` makes stored tokens undecryptable. Plan a
   reconnect/re-encrypt window first.
4. Verify `/health`, one provider read, and one login after rotation.

## Quota and allowance

1. Distinguish seat usage from invoice allowance. They are separate.
2. Trial: 14 days and 25 processed invoices, then read-only plus export.
3. Paid allowance is configurable; do not invent values. Checkout stays gated
   until commercial values are approved.
4. Never block manual AP because an accounting provider is disconnected.
