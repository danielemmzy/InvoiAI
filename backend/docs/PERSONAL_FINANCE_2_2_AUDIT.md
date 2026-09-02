# InvoiAI 2.2 Personal Finance Audit

## Source of truth

The implementation targets the existing Personal Finance 2.0 schema. No new personal-finance SQL migration is required for this release. The existing RLS on the five core tables remains enabled.

Core tables:
- `financial_accounts`
- `financial_transactions`
- `financial_alerts`
- `net_worth_snapshots`
- `statement_imports`

The actual ownership model is `owner_type + owner_id`, not `financial_accounts.org_id`.

## Backend hardening

- All personal finance reads require authenticated workspace context and `VIEW_FINANCE` where appropriate.
- Mutations require `MANAGE_FINANCE`.
- Account IDs are verified against the authenticated owner before transaction insertion.
- Transaction pagination is bounded to 100 rows.
- External transaction IDs preserve database idempotency.
- Synchronous Supabase SDK calls are moved off the FastAPI event loop with `asyncio.to_thread`.
- Redis cache is owner-scoped and invalidated after mutations.
- Cache failures fail open to PostgreSQL; Redis is never the source of truth.
- Cache stampede protection uses a short Redis lock.
- Rate limits are Redis-backed and scoped by client identity/workspace where available.
- Statement reminder is now read-only; it no longer creates database records during a GET.

## AI boundary

Business mode can retrieve business document/vendor/organization semantic memory. Personal mode does not retrieve that semantic context and receives only personal finance tools. The second LLM tool-call pass preserves the same mode.

Chat sessions are also constrained to the authenticated user and active organization.

## Frontend

- React Query cache windows are explicit per data volatility.
- Finance mutations invalidate the workspace finance query family.
- Bank connection remains visible but disabled as `Coming soon`; no fake connection flow is exposed.
- Statement upload remains the primary synchronization mechanism until bank connectivity is launched.
- Recent transaction activity is visible alongside manual entry.

## RLS

Do not remove RLS. The five existing core tables keep RLS enabled. The backend service client is the trusted data-access layer and must remain server-only. Supabase documents that service/secret keys bypass RLS and must never be exposed to browsers.

## Operational requirements

Production should provide a managed Redis instance, TLS, connection limits, monitoring, structured logs, and alerting. PostgreSQL/Supabase remains the durable source of truth.
