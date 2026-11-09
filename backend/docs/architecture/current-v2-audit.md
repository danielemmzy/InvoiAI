# Current V2 Audit — source verification

## V1 boundary

`app/main.py` mounts the current authenticated application routers only under
`/api/v2`, plus `/api/public` for the token-gated vendor portal. It does not
mount a V1 router. Frontend API callers use the Next BFF and the V2 contract;
the only `/api/v1` reference in frontend source is historical documentation.

## V2 work verified in this archive

- V2 domain/repository/mapper/service layers are present for approvals, notifications, finance, insights, integrations, AI/copilot and organization management.
- Container-based dependency composition exists and OCM now resolves OrganizationService through it.
- Scheduler runtime is attached to FastAPI lifespan.
- Notification delivery has durable queue state, atomic claim RPC, retries, failure metadata and stale-processing recovery.
- Finance/insight migration is represented in the repository as `20260814_finance_insight_schema.sql`.
- Organization and vendor V2 HTTP entrypoints are present.
- Public integration response schema no longer exposes OAuth tokens.

## Remaining gates

- Staging schema parity and deployed migration history still need verification before release.
- Full pytest cannot be certified in an environment missing runtime dependencies; run `pip install -r requirements.txt` and then `pytest -q` in the project environment.
- Integration token encryption at rest is still a security hardening task.
- Push/SMS transports remain intentionally unconfigured abstractions.
- Line-item service behavior is covered by focused unit tests; route-level capture integration still needs staged database verification.
- Event-driven AuditWorker is implemented but intentionally not cron-scheduled.
- FinanceWorker remains unimplemented because there is no defined finance background workflow to execute; do not invent business behavior just to fill the file.
