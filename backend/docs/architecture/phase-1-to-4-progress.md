# V2 migration hardening — Phase 1 to Phase 4

This pass implements the first migration-hardening block against the supplied backend ZIP.

## Phase 1 — V1/V2 boundary

- V1 routers are explicitly frozen as `auth`, `billing`, `export`, `history`, `industries`, `invoice`, `stripe_webhook`, and `upload`.
- V1 models are any files directly under `app/models/` outside `app/models/domain/`.
- Added `docs/architecture/v1-v2-migration.md` with the route inventory and removal gate.
- Added `tools/audit_v1_v2.py` to repeat the classification and detect raw database access in V2 services.
- The ZIP has no frontend source tree, so frontend endpoint callers cannot be certified from this artifact. Those callers remain an explicit migration gate before deleting V1 routes.

## Phase 2 — Repository boundary

- `SpendingAnalyzer` no longer reaches through `DocumentRepository.db`.
- Added repository projection methods for spending analysis and embedding backfill.
- `HealthService` now uses `HealthRepository` instead of owning a Supabase client.
- Notification delivery persistence is owned by `NotificationDeliveryRepository`; the duplicate delivery writer was removed from `NotificationRepository`.
- The only remaining direct database access reported by the audit tool is in `services/notification/queue/database_queue.py`, which is intentionally the queue infrastructure boundary.

## Phase 3 — Dependency injection

- Added `app/core/container.py` as the V2 composition root.
- Scheduler workers are resolved lazily through the container instead of being instantiated with missing constructor arguments at module import time.
- V2 routers for approvals, members, finance, insights, and copilot use container-managed services instead of constructing services/repositories inside endpoint handlers.
- Search/Copilot/ToolExecutor dependency construction was corrected so `EmbeddingService` receives its required repository and finance/insight tools share the composed services.

## Phase 4 — Worker infrastructure

The following workers now have explicit orchestration boundaries and scheduler-safe entrypoints where applicable:

- OCR
- Analysis
- Embedding
- Vendor
- QuickBooks
- Xero
- Notification
- Reminder
- Escalation
- Audit
- Insight
- Token refresh
- Memory
- Approval

Worker infrastructure now includes:

- shared retry behavior through `BaseWorker`
- bounded fan-out methods for scheduled workers
- dependency injection through the composition root
- durable notification claim/ack/retry state
- stale notification-processing recovery
- scheduler runtime startup/shutdown through FastAPI lifespan

## Database action still required

The archive now includes both notification-delivery and finance/insight migrations. Supabase remains authoritative; these migrations must be applied/verified there.

## Verification performed in this environment

- Python `compileall` passes for application and test source.
- Notification delivery mapper smoke test passes.
- Full pytest could not run because the execution environment does not have the project's runtime dependencies installed (`slowapi` and `supabase` were missing). This is an environment limitation, not a claim that the test suite is green.
