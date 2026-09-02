# V1 → V2 Migration Boundary

This document freezes the legacy V1 architecture while V2 is migrated and verified.

## V1 classification rules

- Routers listed below are V1 and must not receive new business logic.
- Any model under `app/models/` that is not under `app/models/domain/` is V1.
- V2 persistence follows `Router → Service → Repository → Mapper → Domain Model`.
- Workers orchestrate; they do not own business rules or raw database access.
- V1 routers are not removed until their endpoint replacement is verified.

## V1 router inventory

| Router | Endpoint | Status | V2 target/action | Frontend caller |
|---|---|---|---|---|
| `auth` | `POST "/signup", response_model=AuthResponse)` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `auth` | `POST "/login", response_model=AuthResponse)` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `auth` | `POST "/refresh", response_model=AuthResponse)` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `auth` | `POST "/logout")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `auth` | `GET "/me", response_model=UserProfile)` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `billing` | `POST "/checkout")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `billing` | `GET "/subscription")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `billing` | `POST "/cancel")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `export` | `GET "/{invoice_id}/excel")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `export` | `GET "/{invoice_id}/csv")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `export` | `POST "/{invoice_id}/sheets")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `history` | `GET "")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `industries` | `GET "", response_model=IndustriesResponse)` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `invoice` | `GET "/{invoice_id}", response_model=UploadResponse)` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `invoice` | `DELETE "/{invoice_id}")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `stripe_webhook` | `POST "/webhook")` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |
| `upload` | `POST "", response_model=UploadResponse)` | still required / migration verification pending | map to V2 service/router before removal | **Not available in this ZIP** |

## V1 model inventory

- `app/models/approval.py` — V1 by the project rule (outside `models/domain/`).
- `app/models/audit.py` — V1 by the project rule (outside `models/domain/`).
- `app/models/chat.py` — V1 by the project rule (outside `models/domain/`).
- `app/models/context.py` — V1 by the project rule (outside `models/domain/`).
- `app/models/document.py` — V1 by the project rule (outside `models/domain/`).
- `app/models/integration.py` — V1 by the project rule (outside `models/domain/`).
- `app/models/invoice.py` — V1 by the project rule (outside `models/domain/`).

## Current V2 boundary violations found and fixed in this pass

- `SpendingAnalyzer` no longer reaches through `DocumentRepository.db`; its data access is now repository methods.
- Notification delivery now has a single coherent domain model, mapper, repository lifecycle, durable queue and retry/recovery state.
- Scheduler no longer constructs workers with missing dependencies at import time; it resolves them through the V2 composition root.

## Important limitation

The uploaded ZIP contains backend code and tests but no frontend source tree. Therefore frontend callers cannot be proven from this artifact. Do not mark a V1 route obsolete until the frontend repository has been scanned for its HTTP paths.

## Removal gate

A V1 router may be deregistered only when:
1. Every endpoint has a V2 replacement or an explicit compatibility decision.
2. All callers have been migrated.
3. Contract tests pass.
4. No imports remain.
5. The endpoint has been observed without traffic for the agreed deprecation window.
