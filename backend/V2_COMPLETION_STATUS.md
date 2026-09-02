# InvoiAI V2 — Completion Status

## Scope

This archive is the current backend working copy after the V2 architecture work. Database/schema changes are **not executed from this archive**; Supabase remains the authoritative environment for applying and verifying migrations.

## Confirmed V2 areas present in the archive

- Domain-model / schema / mapper / repository / service layering.
- Approval workflow, approval steps, approval history, approval worker and approval router.
- Notification domain model and preferences.
- Notification providers and dispatcher abstraction.
- Durable notification delivery tracking.
- PostgreSQL/Supabase-backed notification queue abstraction.
- Notification worker.
- Notification delivery retry/failure fields and recovery-oriented methods.
- Finance domain/services/router.
- Insight engine: analyzers, detectors, service, repository, schema, router and worker.
- Proactive integration token-refresh worker.
- QuickBooks and Xero workers.
- Copilot router and tool-execution/tool-definition structure.
- Members and integration webhook routers.
- Request correlation ID middleware, rate limiting, request/exception logging and health endpoints.
- V2 authentication context (`AuthContext` / `AuthUser`).

## Corrections made in this archive

- `AuthUser` is exported from `app.context`.
- `AuthUser.plan` is present for remaining V1 compatibility routes while the V1→V2 migration is completed.
- `AuthUser.permissions` now uses a Pydantic `default_factory` rather than a shared mutable default.
- Supabase authentication now maps optional `org_id`, `role`, and `plan` metadata when available instead of constructing an incompatible `AuthUser` with unrelated fields.
- Authentication does not invent organization membership when the token does not contain it; authoritative V2 membership resolution still belongs to the organization/profile layer.

## Remaining work before V2 can honestly be called production-complete

1. Finish the remaining centralized dependency-injection audit; OCM now resolves OrganizationService from the V2 container.
2. Verify scheduler startup/shutdown and every scheduled worker in an environment with project dependencies installed.
3. Reconcile all V2 repositories/models/services with the confirmed Supabase schema and indexes.
4. Complete notification reliability tests: atomic claiming, retry/backoff, max-attempt terminal state, stale-processing recovery, provider response/error persistence and idempotency.
5. Keep the notification queue as the only intentional V2 raw-DB infrastructure boundary; continue auditing new services for violations.
6. Complete V2 unit, repository, service, worker and integration tests; run the full suite in an environment with all dependencies installed.
7. Migrate remaining V1 routers only after frontend callers have been identified and moved:
   - auth
   - billing
   - export
   - history
   - industries
   - invoice
   - stripe_webhook
   - upload
8. Remove/deprecate V1 models that are still reachable after route migration.
9. Complete frontend/API contract migration and verify every endpoint used by the frontend.
10. Perform final security/RLS/rate-limit/secrets/idempotency/observability audit.
11. Run a clean deployment/startup test and migration test against the actual Supabase environment.

## Important distinction

The existence of V2 files does not by itself mean the V2 migration is complete. The remaining completion gate is: **bootable application + constructible workers + verified database schema + passing tests + migrated frontend callers + retired V1 routes + production hardening**.


## Additional hardening completed in the latest archive

- Added V2 organization current-context HTTP entrypoints.
- Added V2 vendor read/update/preferred/blocked HTTP entrypoints backed by VendorService/Repository.
- Added idempotent finance + insight Supabase migration alongside notification delivery migration.
- Replaced notification queue per-row claim loops with the atomic PostgreSQL claim function.
- Fixed notification delivery queue payload persistence so workers receive title/message/template/data.
- Fixed the in-app provider to conform to the full provider interface.
- Removed OAuth access/refresh tokens from the public integration response schema.
- Normalized requirements.txt to UTF-8 and explicitly included slowapi.

## Integration OAuth HTTP boundary — completed

- Added `app/routers/integrations.py`.
- Added organization-scoped QuickBooks and Xero OAuth connect/callback endpoints.
- Added signed, short-lived OAuth state containing user, organization, provider, and expiry.
- Added connection listing without access/refresh tokens in the response schema.
- Added organization-scoped disconnect with provider revoke before deletion.
- Added `IntegrationService` as the application-layer orchestration boundary.
- Registered the router and service in the V2 composition root.
- OAuth callbacks trigger the existing provider worker for the initial sync while the scheduler remains the recurring-sync mechanism.

**Remaining integration hardening:** encrypt OAuth tokens at rest and replace process-local background-task first-sync execution with a durable job queue when the application's durable job infrastructure is finalized.


## OAuth Token Security — completed in this pass

- Added `app/services/token_service.py`.
- OAuth access/refresh tokens are encrypted with AES-256-GCM before persistence.
- `TOKEN_ENCRYPTION_KEY` is required and must be a base64url-encoded 32-byte key.
- Token refresh now decrypts through `TokenService`, calls the provider, and re-encrypts refreshed credentials before persistence.
- QuickBooks/Xero API clients obtain decrypted access tokens through `TokenService`.
- Integration disconnect decrypts only at the provider-revoke boundary.
- Added `scripts/encrypt_integration_tokens.py` for one-time migration of existing plaintext rows.
- Added `scripts/generate_token_encryption_key.py`.
- Added token encryption unit tests.
- Full pytest execution remains blocked in this packaging environment because `slowapi` is not installed; compileall passes.


## Infrastructure hardening completed in this revision

- Added canonical `/api/v2/*` routes and `/api/v1/*` frozen V1 routes.
- Kept temporary root compatibility aliases, marked deprecated in OpenAPI.
- Updated QuickBooks, Xero and Google OAuth callback defaults to `/api/v2/*`.
- Fixed Redis configuration bug (`settings.REDIS_URL` -> `settings.redis_url`).
- Redis connection now honors `redis_max_connections`.
- SlowAPI rate limiting now uses Redis-backed shared storage.
- Added targeted V2 limits for document upload, copilot chat, integrations and read-heavy endpoints.
- Added Redis cache key conventions and cache invalidation support.
- Added cache-aside caching for industries, vendors, insights and organization reads/permissions.
- Kept secrets, OAuth tokens and raw documents out of cache.
- Added infrastructure regression tests: `tests/test_v2_api_infrastructure.py` (4 passing).
- Added architecture documentation: `docs/ARCHITECTURE_V2_API_REDIS.md`.

### Important deployment requirement

Set `REDIS_URL` in production. Redis is now part of the V2 shared infrastructure for distributed rate limiting and caching.


## V1 → V2 HTTP Migration — 2026-08-16

Frontend API clients now use `/api/v2` as their canonical base path.

Migrated frontend capabilities:
- document upload/list/detail/archive-delete
- industries
- export (Excel/CSV/Google Sheets)
- authentication
- billing
- existing V2 integrations, approvals, members, finance, insights, copilot, vendors

Removed from FastAPI application routing:
- V1 upload
- V1 invoice
- V1 history
- V1 export
- V1 industries
- V1 auth
- V1 billing
- V1 stripe_webhook

The old V1 router modules have been removed from `app/routers/`. Remaining V1 model/service references must be handled only if a later static dependency audit proves they are still reachable by V2 code.
\n\n## 2026-08-16 Production hardening update\n\n- Added Redis-backed distributed scheduler locks with ownership-safe release and TTL heartbeat renewal.\n- Added production scheduler lock settings: `SCHEDULER_LOCK_ENABLED`, `SCHEDULER_LOCK_TTL_SECONDS`, `SCHEDULER_LOCK_FAIL_OPEN`.\n- Added `scripts/generate_token_encryption_key.py --write-env` for safe local key generation without committing secrets.\n- Added production Redis/Upstash setup documentation and OAuth token-encryption setup documentation.\n- Added a distributed-lock unit test.\n- The archive intentionally contains no real OAuth/Redis/Stripe/Supabase secrets.\n- Full real-dependency test execution still requires installing `requirements.txt` in an environment with the external packages available and supplying test credentials/services.\n