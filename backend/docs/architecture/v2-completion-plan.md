# InvoiAI V2 — completion plan after latest archive hardening

Legend: ☑ verified/present in this archive · ☐ remaining gate

## 1. V1/V2 migration boundary

☑ Freeze V1 router set:
- auth
- billing
- export
- history
- industries
- invoice
- stripe_webhook
- upload

☑ V1 model rule: files directly under `app/models/` are V1; `app/models/domain/` is V2.

☑ Repeatable V1/V2 audit tool exists.

☑ V1 endpoint inventory exists.

☐ Scan the frontend repository and map every V1 endpoint caller.

☐ Decide each V1 endpoint: migrated / compatibility-only / obsolete / still required.

☐ Migrate required V1 endpoints to V2.

☐ Deregister obsolete V1 routers only after contract tests and frontend verification.

## 2. V2 layering / repository boundary

☑ Domain models, mappers, repositories and services exist across the main V2 areas.

☑ Services/analyzers audited for direct DB access.

☑ Notification queue is intentionally the remaining raw-DB infrastructure boundary.

☐ Continue the repository audit as new V2 functionality is added.

## 3. Dependency injection

☑ V2 composition root: `app/core/container.py`.

☑ Scheduler workers resolve through the container.

☑ OCM resolves OrganizationService through the container.

☑ Major approval, notification, finance, insight and copilot dependencies are composed centrally.

☐ Remove unnecessary fallback `Service()` construction from production paths where concrete dependencies are always available.

☐ Add automated composition/boot tests.

## 4. Workers

☑ BaseWorker retry/logging abstraction.

☑ OCR, Analysis, Embedding, Vendor, QuickBooks, Xero workers.

☑ Approval, Notification, Reminder, Escalation, Insight, Token Refresh, Memory workers.

☑ Scheduled workers have bounded fan-out methods where their workload is defined.

☑ Notification worker has durable claim/retry/recovery lifecycle.

☑ Scheduler runtime starts/stops with FastAPI lifespan.

☐ Define and implement FinanceWorker only when a real finance background workflow is specified.

☐ Add automated worker construction tests.

☐ Add concurrency/idempotency tests for each durable worker.

☐ Add stale-job recovery tests for non-notification workers that use durable job state.

## 5. Notifications

☑ Notification domain model/preferences.

☑ Notification service/repository/mapper.

☑ Provider interface.

☑ In-app and email providers.

☑ Push/SMS provider abstractions intentionally return unavailable until configured.

☑ Notification dispatcher.

☑ Durable `notification_deliveries`.

☑ Atomic PostgreSQL claim function.

☑ Retry/backoff/max-attempt state.

☑ Provider error/message tracking fields.

☑ Stale-processing recovery.

☑ Idempotency key.

☑ Queue payload persistence fixed.

☐ Add provider-result objects if provider message IDs/statuses need to be captured from external providers.

☐ Add end-to-end notification tests.

## 6. Finance / Insight database

☑ Finance tables created in Supabase per confirmed schema.

☑ Insight table created in Supabase per confirmed schema.

☑ Finance and insight enums confirmed.

☑ Repository migration file added to the archive for reproducibility:
`migrations/20260814_finance_insight_schema.sql`

☑ Notification migration remains:
`migrations/20260813_notification_delivery_infrastructure.sql`

☐ Verify the migration files against the actual Supabase schema before production deployment.

## 7. Finance / Insight application layer

☑ Finance domain models/mappers/repositories/services/router.

☑ Insight analyzers/detectors/service/repository/router/worker.

☑ Finance/Insight V2 routes are registered.

☐ Full repository/service integration tests.

## 8. Organization / Vendor / Integration HTTP boundary

☑ Organization current-context/permissions V2 router.

☑ Vendor V2 read/update/preferred/blocked router.

☑ Integration webhook router.

☐ Full OAuth connect/callback/disconnect V2 service boundary.

☐ Encrypt integration access/refresh tokens at rest.

☐ Never return OAuth tokens in API response models (the public response schema is now hardened).

## 9. Security

☑ JWT validation boundary exists.

☑ Request correlation IDs.

☑ Rate limiting middleware.

☑ Exception/request logging.

☑ OAuth tokens removed from public integration response schema.

☐ Add encrypted token-at-rest service.

☐ Audit organization isolation/RLS.

☐ Audit authorization on every V2 endpoint.

☐ Verify webhook signature configuration for every provider.

☐ Verify secrets are excluded from logs.

## 10. Tests / release gate

☑ Compileall passes for app and tests.

☑ Notification mapper smoke test passes.

☐ Install project dependencies in the real project environment.

☐ Run full `pytest -q`.

☐ Fix all failing tests.

☐ Add repository integration tests against Supabase.

☐ Add service tests.

☐ Add worker tests.

☐ Add notification retry/recovery tests.

☐ Add API contract tests.

☐ Add end-to-end upload → OCR → analysis → approval → export → billing test.

☐ Run clean application startup test.

☐ Run migration verification against Supabase.

## 11. V1 retirement

☐ Frontend callers identified.

☐ V1 endpoint migration complete.

☐ Compatibility window completed.

☐ Obsolete V1 routers removed.

☐ Obsolete V1 models/services removed.

☐ Final import/dependency scan confirms no V2 path depends on V1-only implementations.

## Final V2 completion definition

V2 is complete only when all remaining gates above are green:

**bootable + migrations verified + tests green + secure token handling + frontend migrated + V1 retired + worker/scheduler reliability verified.**
