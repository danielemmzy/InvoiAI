# Current V2 Audit — archive verification

## V1 boundary

Frozen V1 routers:
- auth
- billing
- export
- history
- industries
- invoice
- stripe_webhook
- upload

Any model directly under `app/models/` outside `app/models/domain/` is V1 by project rule.

## V2 work verified in this archive

- V2 domain/repository/mapper/service layers are present for approvals, notifications, finance, insights, integrations, AI/copilot and organization management.
- Container-based dependency composition exists and OCM now resolves OrganizationService through it.
- Scheduler runtime is attached to FastAPI lifespan.
- Notification delivery has durable queue state, atomic claim RPC, retries, failure metadata and stale-processing recovery.
- Finance/insight migration is represented in the repository as `20260814_finance_insight_schema.sql`.
- Organization and vendor V2 HTTP entrypoints are present.
- Public integration response schema no longer exposes OAuth tokens.

## Remaining gates

- Frontend is not present in this archive, so V1 route callers cannot be certified.
- V1 routers remain mounted until endpoint-by-endpoint migration is verified.
- Full pytest cannot be certified in an environment missing runtime dependencies; run `pip install -r requirements.txt` and then `pytest -q` in the project environment.
- Integration token encryption at rest is still a security hardening task.
- Push/SMS transports remain intentionally unconfigured abstractions.
- LineItemService remains incomplete because no stable application-level create/update contract was supplied by the extraction pipeline.
- Event-driven AuditWorker is implemented but intentionally not cron-scheduled.
- FinanceWorker remains unimplemented because there is no defined finance background workflow to execute; do not invent business behavior just to fill the file.
