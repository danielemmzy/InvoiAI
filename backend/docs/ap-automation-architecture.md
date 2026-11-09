# InvoiAI Accounts Payable — Architecture and Recovery Plan

**Status:** living document. Phases 0a-0d implemented 2026-11-04/05; Phases 1-2 planned.
**Scope:** the AP pipeline that runs after a document is identified as an invoice:
matching → GL coding → approval → ERP sync → payment. OCR, extraction and document
classification are upstream and only included where they interact with AP state.
**Audience:** whoever operates or extends the AP feature. No accounting background
is assumed; the glossary is part of the spec.

---

## 1. The 90-second version

InvoiAI's AP pipeline is a **state machine stored on `documents.ap_status`**, advanced
by two workers (matching and GL coding). A user starts it from the AP page; the API
launches it with `asyncio.create_task`, and the browser watches the document row until
`processing_step` reaches a terminal label.

The pipeline is logically sound but operationally incomplete:

1. **No chart of accounts by default.** GL coding is only allowed to pick an existing
   account. A new organization starts with zero accounts, so every line ends in
   "needs human review", and the invoice appears stuck at 85%.
2. **The workers are never scheduled.** `run_pending()` exists on both AP workers, but
   the in-process cron registers no AP job. If the API process restarts — or a task is
   lost — nothing picks the invoice up again.
3. **The API process is the queue.** Work is started with fire-and-forget
   `asyncio.create_task`. A restart, deploy, or crash loses the task even though the
   database still says "in progress".
4. **The retry endpoint refuses to retry "in progress" work.** `/ap/documents/{id}/run`
   intentionally returns the current status instead of re-dispatching, and there is no
   stale-lease rule to decide when "in progress" is actually dead.
5. **Document Intelligence and AP share the same progress fields.** OCR/extraction
   writes `processing_step`, `processing_message`, `processing_progress`, and `status`.
   A late upstream update can overwrite "AP coding" with "Analysis complete".

The fix is not a rewrite. It is: give the org a chart of accounts, make the database
the source of truth for pending work, add cron sweepers with leases/backoff, stop
upstream processing from writing AP progress, then drain the stuck invoices.

---

## 2. Glossary

| Term | Plain meaning | Where it lives |
|---|---|---|
| **AP (Accounts Payable)** | Money the business owes suppliers. The AP feature tracks a supplier invoice from arrival to payment. | `documents`, `ap_*` tables |
| **Vendor** | The supplier who sent the invoice. | `vendors` |
| **Invoice / bill** | The supplier's request for payment. In this codebase an AP invoice is a `documents` row with `document_type = 'invoice'` and `ap_enabled = true`. | `documents` |
| **Line item** | One row of the invoice: description, quantity, unit price, amount. Coding happens per line. | `document_line_items` |
| **PO (purchase order)** | What the business ordered from the vendor. | `purchase_orders` |
| **Goods receipt** | Confirmation that ordered goods actually arrived. | `goods_receipts` |
| **2-way match** | Invoice ↔ PO (price/quantity ordered). | `matching_service.py` |
| **3-way match** | Invoice ↔ PO ↔ goods receipt (price + quantity received). | `matching_service.py` |
| **Match exception** | A difference outside tolerance (price, quantity, missing PO, duplicate). The invoice stops for a human. | `invoice_exceptions` |
| **GL account** | A bucket in the accounting ledger, e.g. `6100 Software & Subscriptions`. Every line must point at one before it can post. | `chart_of_accounts` |
| **Chart of accounts (COA)** | The full list of GL accounts a business uses. It is the vocabulary of accounting: without it there is no legal place to put an expense. | `chart_of_accounts` |
| **Coding** | Choosing the GL account (and optionally department/cost centre/project/tax) for each invoice line. | `invoice_codings` |
| **Coding rule** | "If vendor is X and description contains Y, use account Z." Deterministic, no AI. | `coding_rules` |
| **Exception** | A structured blocker that a human must resolve. The invoice stays in `match_exception` or `coding_exception` until it is. | `invoice_exceptions` |
| **Approval workflow** | The chain of people who must approve the bill/payment, based on rules, limits and groups. | `approval_*` tables |
| **Payment instruction** | The instruction to pay an approved bill, with its own state machine. | `payment_instructions` |
| **ERP sync** | Pushing the coded bill to QuickBooks/Xero as a bill. | `erp_bill_id`, sync workers |
| **`ap_status`** | The AP state machine position. This is authoritative. | `documents.ap_status` |
| **`processing_*`** | Presentation progress (`processing_step`, `processing_message`, `processing_progress`). Shared with Document Intelligence; **not** authoritative. | `documents` |

**Why the COA matters:** accounting is double-entry. Coding a line means "debit this
expense account, credit accounts payable." If the account does not exist, there is no
valid journal entry, so a correct AP system must refuse to auto-code. That is exactly
what InvoiAI does — the bug was that no starter chart was ever created.

---

## 3. Current architecture (as built)

```
 Upload / email / API
        │
        ▼
 ┌─────────────────────────────┐
 │ Document Intelligence       │  OCR → extraction → analysis → classification
 │ (cron: ocr, vendor,         │  Writes: status, processing_step/message/progress,
 │  analysis, embedding, ...)  │          document_analyses, document_line_items
 └──────────────┬──────────────┘
                │ user opens AP page and starts AP
                ▼
 ┌─────────────────────────────┐
 │ POST /ap/documents/{id}/run │  chooses match mode, PO, receipt
 │ (routers/ap.py)             │  sets ap_status=validating, processing_*=ap_validating
 └──────────────┬──────────────┘
                │ asyncio.create_task(_run_explicit_ap_workflow)
                │ Redis lock invoiai:ap:workflow:{id}, TTL 900s
                ▼
 ┌─────────────────────────────┐     ┌───────────────────────────┐
 │ APMatchingWorker            │────▶│ match_exception?          │
 │ validating → matching       │     │   yes: invoice_exceptions │
 └──────────────┬──────────────┘     └───────────────────────────┘
                │ coding
                ▼
 ┌─────────────────────────────┐     priority in _code_line:
 │ APCodingWorker              │       1. manual account on the line
 │ coding → coding_exception   │       2. coding rules
 │        → awaiting_approval  │       3. vendor history (last 25 docs)
 └──────────────┬──────────────┘       4. OpenAI gpt-4o-mini (optional)
                │                      5. else needs_review
                ▼
 ┌─────────────────────────────┐
 │ Approval workflow           │  approval rules/limits/groups
 │ awaiting_approval → approved│
 └──────────────┬──────────────┘
                ▼
 ┌─────────────────────────────┐
 │ ERP sync / payment          │  QuickBooks/Xero bill + payment instruction
 │ syncing_to_erp → payment_ready → paid → reconciled
 └─────────────────────────────┘
```

### Step responsibilities

| Step | Code | Reads | Writes | Failure mode today |
|---|---|---|---|---|
| Dispatch | `routers/ap.py: run_ap` | document, PO/receipt choice | `ap_status=validating`, progress fields | lost task; no re-dispatch while status is in-progress |
| Match | `workers/ap_matching_worker.py` | invoice lines, PO, goods receipt | `ap_status`, `match_status`, exceptions, progress | raises inside task; outer workflow only catches coding errors |
| Code | `workers/ap_coding_worker.py` → `services/ap/gl_coding_service.py` | lines, rules, history, COA | `invoice_codings`, `gl_coding_status`, `ap_status`, exceptions | no COA → every line `needs_review`; OpenAI failure silently falls through |
| Approve | `services/ap/approval_bridge.py`, approval workers | codings, rules, limits | approval rows, `ap_status` | not exercised in the stuck-invoice case |
| Sync | QuickBooks/Xero workers | approved bill | `erp_bill_id`, `ap_status` | out of scope for Phase 0 |

### Authoritative state

`documents.ap_status` is the truth. `processing_step` is a label for the UI and is
written by many features; it must never be used to decide whether work is pending.

The state machine (`services/ap/invoice_state_machine.py`) enforces:

```
received → extracting → validating → matching → coding → awaiting_approval
                                   ↘ match_exception ↗        ↘ approved
coding → coding_exception → coding | awaiting_approval
awaiting_approval → approved | rejected | on_hold
approved → syncing_to_erp | payment_ready
syncing_to_erp → payment_ready | approved
payment_ready → paid → reconciled → payment_ready (provider-confirmed reversal)
on_hold → matching | coding | awaiting_approval | rejected
rejected → (terminal)
```

Each transition writes an `invoice_status_log` row. This is the audit trail; keep it.

### Where the data lives

- `documents` — one row per invoice; `ap_status`, `ap_enabled`, `ap_match_mode`,
  `match_status`, `gl_coding_status`, `processing_*`, `erp_bill_id`.
- `document_line_items` — the lines being coded; may carry a reviewer-selected
  `gl_account_id` / `gl_account_code` / `gl_account_name`.
- `invoice_codings` — one coding per line with `source`, `confidence`, `status`,
  dimensions and `coding_rule_id`.
- `coding_rules` — deterministic vendor/description/SKU → account mappings.
- `chart_of_accounts` — the allowed destinations; `is_postable` gates use.
- `invoice_exceptions` — structured blockers with status and resolution.
- `invoice_status_log` — append-only AP state transitions.
- `purchase_orders`, `goods_receipts` — match references.
- `approval_*`, `payment_instructions` — downstream lifecycle.

---

## 4. Defects found (with evidence)

### D1 — No chart of accounts is created for an organization (P0)

**Symptom:** invoice sits at `ap_status=coding`, `gl_coding_status=pending`,
`match_status=pending`, `processing_step=complete`, progress 100.
**Root cause:** `chart_of_accounts` had **0 rows** for org
`94df654e-25b9-404b-bb21-45568959e559`; all 4 line items were uncoded and one
`invoice_codings` row was stale. `GLCodingService` can only select from existing
accounts, and `POST /ap/chart-of-accounts/sync` requires a connected QuickBooks.
**Impact:** no new organization can ever auto-code. This is the first thing to fix.

### D2 — AP runs as fire-and-forget tasks (P0)

**Symptom:** after a restart/deploy the invoice stays "in progress" forever.
**Root cause:** `asyncio.create_task(_run_explicit_ap_workflow(...))` in
`routers/ap.py`. A Redis lock prevents duplicates for 900 s, but no durable job exists.
**Impact:** any process lifecycle event silently drops work; the DB has no record that
the task died.

### D3 — `run_pending()` is dead code (P0)

**Symptom:** nothing retries orphaned invoices.
**Root cause:** both `APMatchingWorker.run_pending` and `APCodingWorker.run_pending`
exist, but `scheduler/periodic_jobs.py` registers 15 jobs and none of them is AP.
**Impact:** recovery depends entirely on a human clicking the right button.

### D4 — `/run` cannot recover an in-progress invoice (P0)

**Symptom:** re-running returns the same status; no progress.
**Root cause:** `run_ap` refuses to dispatch when the document is already in an AP
state. There is no lease/heartbeat, so the API cannot distinguish "working" from
"abandoned".
**Impact:** the only recovery path is manual database surgery.

### D5 — Document Intelligence overwrites AP progress (P1)

**Symptom:** an AP invoice shows "Analysis complete", progress 100, while AP is at
coding. That is exactly what the stuck invoice showed.
**Root cause:** both features write `processing_step`, `processing_message`,
`processing_progress` and `status` on `documents`. `DocumentRepository.update_processing_state`
has no AP guard. A late analysis/embedding pass wins the race.
**Impact:** misleading UI, support burden, and tests that cannot trust `processing_step`.

### D6 — GL coding depends on OpenAI by default (P1)

**Symptom:** with exhausted OpenAI credits, the last coding fallback fails; logs show
`GL coding AI suggestion failed`.
**Root cause:** `GLCodingService._ai_suggest` hardcodes `gpt-4o-mini` and the shared
OpenAI client. Failure is caught and returns `None`, so it degrades to `needs_review`
rather than crashing — but a new org with no rules/history has no other path.
**Impact:** coding is not deterministic for a fresh org. The fix is a COA + rules, and
optionally a provider-agnostic AI fallback. AI should never be the only path.

### D7 — Exceptions can outlive the condition (P2)

**Symptom:** a resolved match/coding exception may remain open while the invoice moves
on.
**Root cause:** exceptions are created in several places; resolution is manual/partial.
**Impact:** dashboards overstate blockers and users re-resolve resolved issues.

### D8 — No operational visibility (P2)

**Symptom:** no metric/alert for "AP invoice older than N minutes in a non-terminal
state".
**Root cause:** AP progress is only visible by reading a document row.
**Impact:** incidents are found by users, not by the system.

---

## 5. Target architecture

```
 ┌──────────────────────────┐
 │ Document Intelligence    │  writes only DI-owned fields; never AP fields
 └────────────┬─────────────┘
              ▼
 ┌──────────────────────────┐
 │ AP Orchestrator          │  one entry point for every trigger:
 │ enqueue(document_id,     │  user action, cron recovery, webhook
 │  reason)                 │  persists intent in the document row
 └────────────┬─────────────┘
              ▼
 ┌──────────────────────────┐      ┌─────────────────────────────┐
 │ Cron sweeper (1 min)     │─────▶│ Pending AP work query       │
 │ lease + backoff          │      │ ap_status IN (validating,   │
 └────────────┬─────────────┘      │ matching, coding) AND       │
              │                    │ updated_at < now - lease    │
              ▼                    └─────────────────────────────┘
 ┌──────────────────────────┐
 │ Idempotent step runner   │  each step checks current state and
 │ match → code → approval  │  re-enters safely; no duplicate codings
 └────────────┬─────────────┘
              ▼
 ┌──────────────────────────┐
 │ Exceptions / approval    │  human resolves; resolution re-enqueues
 └──────────────────────────┘
```

Design rules:

1. **The database is the queue.** A document in a non-terminal `ap_status` with an old
   `updated_at` is pending work. Redis locks are an optimization, not the source of
   truth.
2. **Every step is idempotent.** Re-running matching must not duplicate exceptions;
   re-running coding must upsert by `(document_id, line_item_id)` and must preserve
   manual selections (it already does for manual accounts).
3. **One progress writer per phase.** AP writes `ap_status` and (after 0c) its own
   `ap_processing_*` fields, or writes `processing_*` only while no DI job is active.
   DI must not touch AP rows.
4. **No unbounded tasks.** The request handler may kick a background run, but cron is
   the safety net. A restarted process loses nothing that matters.
5. **AI is optional.** Rule → history → manual works with zero AI. Add AI only as a
   ranked suggestion with a confidence threshold and a provider-agnostic client.
6. **Exceptions are the interface.** Every blocker is a row with a type, severity,
   owner and resolution path. "Stuck" should be impossible; it should be "blocked on X".

---

## 6. Phased plan

### Phase 0a — Starter chart of accounts + CRUD UI (implemented)

**Goal:** a new organization can load a usable chart and edit it, so coding has real
destinations.

Backend:

- `app/services/ap/chart_of_accounts_seed.py`
  - `STARTER_ACCOUNTS`: 24 standard small-business accounts (assets, liabilities,
    equity, revenue, COGS, operating expenses), all postable.
  - `missing_starter_accounts(existing_codes)`: pure, testable diff.
  - `seed_starter_chart_of_accounts(org_id, db=None)`: additive and idempotent; skips
    existing codes; never modifies a user-edited row.
- `app/routers/ap.py`
  - `GET /ap/chart-of-accounts?include_inactive=true`
  - `POST /ap/chart-of-accounts/seed` (idempotent; invalidates the COA cache)
  - `POST /ap/chart-of-accounts` (validates `account_type`)
  - `PATCH /ap/chart-of-accounts/{id}` (validates `account_type`, org-scoped)
  - `DELETE /ap/chart-of-accounts/{id}` (soft-deactivate; history keeps references)
- Tests: `tests/test_ap_chart_of_accounts_seed.py` — uniqueness/classification,
  diff behavior, idempotent no-op, org-scoped inserts.

Frontend:

- `src/app/dashboard/settings/accounting/page.tsx` — search, show-inactive, add/edit
  form, deactivate/reactivate, empty state with "Load starter chart of accounts".
  Uses React Query with workspace-scoped cache keys.
- `src/app/dashboard/settings/page.tsx` — "Chart of Accounts" link card.
- `src/api/ap.ts` — COA list/seed/create/update/deactivate methods.
- `src/hooks/useAP.ts` — `useChartOfAccounts` queryFn fixed for the new list signature.

**Acceptance:** seed twice → second call creates 0, existing rows unchanged; create,
rename, deactivate and reactivate an account; coding sees the seeded accounts; ESLint
and TypeScript clean for the touched files.

**Explicitly not in 0a:** auto-seeding on signup (that is an onboarding decision), COA
import from CSV, account hierarchy UI, tax-code mapping UI.

### Phase 0b — Durable AP recovery (implemented 2026-11-04)

1. Added `app/services/ap/recovery_service.py`:
   - `list_stale(now, lease_seconds=900)` selects documents where
     `ap_enabled = true`, `document_type = 'invoice'`,
     `ap_status IN ('validating','matching','coding')`,
     `updated_at < now - lease`.
   - Re-dispatches **one** idempotent step at a time (`matching` then `coding`).
   - Retry/backoff lives in Redis (`invoiai:ap:recovery:v1:<document_id>`), so the
     database stays authoritative and a Redis outage degrades to retrying next sweep.
   - Exponential backoff `60s -> 120s -> 240s -> 480s -> 900s`.
   - After `AP_RECOVERY_MAX_ATTEMPTS` (default 5), the document is moved to
     `coding_exception` or `match_exception`, progress is written, and a
     `gl_coding_required` exception is opened for coding failures. It never stays
     silently stuck in `coding`/`matching`.
2. Registered `cron.register(name="ap-recovery", expression="* * * * *", worker=...)`.
3. Made dispatch idempotent:
   - `/run` re-dispatches when the in-progress lease is stale, and can restart an
     abandoned `match_exception`/`coding_exception` that has no open exception row.
   - The sweeper takes a Redis sweep lock; the per-document worker locks still apply.
4. Matching resumes from `validating` **or** `matching`, so an interrupted run continues.
5. Matching exceptions use `upsert_open`, so a retry refreshes the same finding
   instead of duplicating it.
6. Human resolution clears the recovery marker before re-dispatching.

**Acceptance:** kill the API mid-coding, restart, and the sweeper finishes the invoice
within 2 minutes; no duplicate codings; no duplicate exceptions; a permanently failing
invoice stops after N attempts with one visible exception.

**Explicitly not in 0b:** a separate worker process, a new queue, or a new database
table. The DB row + the existing cron are sufficient.


### Phase 0c — Separate AP and Document Intelligence progress (implemented 2026-11-04)

The shared `processing_*` columns are kept (no schema change), but ownership is now
explicit and enforced in one place:

1. `DocumentRepository.update_processing_state` checks the document's `ap_enabled`
   and `ap_status`. Once AP is in `validating`, `matching`, `coding`, or any later
   state, a non-AP step is dropped instead of overwriting the AP page. Steps named
   `ap_*` are always allowed.
2. The three explicit Document Intelligence entry points (`run intelligence`, failed
   retry, and the legacy OCR alias) reject AP-owned invoices with `409` and a clear
   message, so DI cannot reset progress to `queued`/`0`.
3. AP keeps using the existing columns and labels; the AP page needs no change.
4. Regression coverage: `tests/test_ap_progress_isolation.py` proves an analysis
   write at `coding` is ignored, an `ap_*` write is kept, and DI still writes before
   AP starts.

**Acceptance:** no DI job can change AP-visible progress; document list and AP page
show consistent, phase-correct labels.

**Explicitly not in 0c:** new `ap_processing_*` columns. That would require a
deployed schema migration; the guard gives the same isolation without one.


### Phase 0d — Drain the stuck invoice (implemented 2026-11-05)

Executed against invoice `f1badae1-44c7-4f9a-997e-12254d6305e1`:

1. Seeded the org's 24-account starter COA and confirmed `1200 Inventory`.
2. Inspected the four J/S line items and the orphan `invoice_codings` row; removed
   only the orphan, then assigned all four lines to `1200 Inventory` per the owner.
3. Re-ran `APCodingWorker`: `gl_coding_status=auto_coded`, four approved codings.
4. Resolved the stale `gl_coding_required` exception with the owner's authority and
   a note recording the coding decision.
5. Submitted through `APApprovalBridge` exactly as the UI button does. The invoice
   is now `awaiting_approval` with one `in_review` workflow and a pending owner step.

Submission exposed four real defects, all fixed with regression tests:

- `APRoutingEngine.build_plan` called the nonexistent
  `ApprovalRuleRepository.list_active_rules`; it now loads via
  `list(org_id, scope=..., active_only=True)` and converts rows with
  `approval_rule_from_row` (`tests/test_ap_routing_engine_rules.py`).
- The no-rules fallback filtered `org_members.role` on `finance_manager` and
  `ap_manager`, which the deployed `org_role` enum rejects. Roles are now filtered
  in Python so the query works across schema versions.
- The bill and payment workflow builders omitted `ApprovalStep.created_at`; both
  now set it.
- `ApprovalWorkflow`/`ApprovalStep` forbade the `created_at`/`updated_at` columns
  the database returns, so the workflow row was inserted but could not be read
  back. The models now accept those timestamps
  (`tests/test_approval_model_timestamps.py`). `create_workflow` also treats a
  step-less workflow as an interrupted creation and replaces it instead of
  returning a broken workflow.

**Acceptance:** invoice `f1badae1-44c7-4f9a-997e-12254d6305e1` reached
`awaiting_approval` with every line coded and a pending approval step.

### Phase 1 — Production hardening

- Idempotency keys on approval/payment actions; no double payment instructions.
- Optimistic concurrency on `ap_status` transitions (update-where current status).
- Approval routing tests for limits, groups, segregation of duties.
- ERP sync retry/backoff with a dead-letter state and reconciliation report.
- Audit coverage: who changed an account, a rule, a coding, an approval.
- A "resume from exception" endpoint that validates the precondition and re-enqueues.

### Phase 2 — Scale and intelligence

- Outbox/queue for AP steps (Redis Streams or a managed queue) once volume justifies
  it; keep cron as the reconciler.
- Rule suggestions learned from approved history (human-approved, never auto-applied).
- Vendor normalization and duplicate-invoice detection across orgs? (No — per org only.)
- Cost/quality dashboards for AI suggestions; per-org provider configuration.
- Bulk actions and CSV/ERP COA import.

---

## 7. AI provider strategy (no OpenAI spend required)

Current OpenAI consumers (for awareness, not all need replacing):

| Consumer | File | Criticality | Free/local option |
|---|---|---|---|
| OCR | `services/ocr/openai_ocr_service.py` | High (text extraction) | Tesseract (local), Gemini free tier, Groq vision |
| Extraction | extraction engine | High | deterministic parser + Gemini/Groq |
| Classification | classifier | Medium | rules + small local model |
| GL coding suggestion | `services/ap/gl_coding_service.py` | Low (optional fallback) | disable; COA + rules + history is enough |
| Embeddings / memory | embedding/memory workers | Low for AP | disable for AP; local sentence-transformers |
| Health check | health router | Low | skip |

**Recommended for testing now**

1. **GL coding: turn AI off.** The code path already supports manual, rules and history.
   Add a setting `AP_GL_AI_ENABLED=false` (Phase 0b/0c) and return `needs_review`
   immediately instead of making a doomed request.
2. **If you need OCR/extraction without OpenAI:** point the client at an
   OpenAI-compatible endpoint. Gemini's free tier exposes one:

   ```env
   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   OPENAI_API_KEY=<gemini-key>
   OCR_MODEL=gemini-2.0-flash
   ```

   Verify the exact model name available to your key before relying on it. Groq is a
   drop-in alternative for text; local Ollama is best for privacy but needs hardware.
3. **Fully local:** Tesseract for OCR + regex/table extraction for totals, with manual
   review for anything uncertain. Slower accuracy on photos, zero API cost.

**Design rule:** AI must be a ranked suggestion over the existing COA, with a
confidence threshold, and every AI result must be auditable (`source=ai_suggested`).
Never let AI invent an account code.

---

## 8. Runbook — unsticking an AP invoice

> Use after Phase 0b when possible. Until then, steps 3–5 are manual and must be done
> with a DB backup or in a transaction.

1. **Inspect**

   ```sql
   select id, org_id, ap_enabled, ap_status, match_status, gl_coding_status,
          processing_step, processing_message, processing_progress, updated_at
   from documents where id = '<invoice-id>';

   select count(*) from chart_of_accounts where org_id = '<org-id>' and is_active;
   select id, line_item_id, gl_account_id, source, status
   from invoice_codings where document_id = '<invoice-id>';
   select id, exception_type, status, title
   from invoice_exceptions where document_id = '<invoice-id>';
   ```

2. **Ensure a chart exists**

   `POST /ap/chart-of-accounts/seed` (idempotent) or run
   `seed_starter_chart_of_accounts(org_id)` from the backend venv. Confirm rows exist.

3. **Clear only stale, non-manual codings**

   Delete `invoice_codings` rows whose `source != 'manual'` for lines that are still
   unassigned. Do not touch reviewer-selected accounts.

4. **Re-enter the state machine**

   If `ap_status = coding`, dispatch coding again. If the document is in an in-progress
   status with no worker, move it to `coding` (or `validating` for a full rematch) with
   an `invoice_status_log` reason. Use the state machine so the audit trail is written.

5. **Verify**

   `gl_coding_status` becomes `auto_coded` (or `needs_review` with a single clear
   exception), `ap_status` moves to `awaiting_approval`, and the AP page shows the
   approval step — not "Analysis complete".

6. **If it fails again**

   Read the worker log for the document id. Common causes: no postable accounts, vendor
   has no history and no matching rule, OpenAI timeout, or a `document_line_items` row
   with no amount. Fix the data, not the status.

---

## 9. Operations

- **Cron:** in-process scheduler, 15 jobs today. Phase 0b adds `ap-recovery`.
- **Locks:** Redis keys `invoiai:ap:workflow:{id}` (900 s), `...:coding:{id}` (300 s),
  `...:matching:{id}` (300 s). Locks are not leases; do not treat them as truth.
- **Logs:** `AP workflow already running`, `AP GL coding failed`, `GL coding AI
  suggestion failed`. Add document id + org id to every new log line.
- **Metrics to add:** pending AP count by status, age of oldest pending invoice,
  coding outcomes by source, exception counts, recovery attempts.
- **Alerts:** any invoice in `validating|matching|coding` older than 15 minutes; any
  exception open longer than the org's SLA.

---

## 10. Testing strategy

- **Unit:** seed diff/idempotency (exists); state transitions; rule matching; coding
  priority order; manual-coding preservation.
- **Integration (fake DB/queue):** stale reaper picks exactly the right rows; re-running
  coding does not duplicate; exceptions are not duplicated; DI cannot overwrite AP fields.
- **End-to-end (staging):** upload invoice → start AP → match → code → approve → sync;
  kill the process mid-coding and assert recovery; run with no COA and assert a clear
  exception, not a hang.
- **Contract:** API shapes for COA list/seed/create/update/delete; AP page reads.
- **Failure injection:** Redis unavailable, OpenAI 401/timeout, ERP 500, duplicate webhook.

---

## 11. Open decisions

1. **Ledger source of truth.** Is InvoiAI the system of record for AP, or a feeder to
   QuickBooks/Xero? This determines whether payment and reconciliation belong here.
2. **Onboarding.** Should the starter COA seed automatically on org creation, or stay a
   deliberate action? (0a makes it deliberate; auto-seed is a one-line change plus a
   product decision.)
3. **Payment provider.** Still unselected per the production roadmap; blocks real
   payment execution.
4. **AI data policy.** Which vendor/bank data may leave the environment for OCR/AI?
   This decides cloud vs local models.
5. **Approval scope.** Bill approval only, or bill + payment authorization with
   segregation of duties? The tables exist; the policy does not.

---

## Appendix — Phase 0a file map

```
backend/
  app/services/ap/chart_of_accounts_seed.py      # starter chart + idempotent seed
  app/routers/ap.py                              # COA list/seed/create/update/deactivate
  tests/test_ap_chart_of_accounts_seed.py        # 4 passing tests
frontend/
  src/app/dashboard/settings/accounting/page.tsx # COA settings UI
  src/app/dashboard/settings/page.tsx            # settings link card
  src/api/ap.ts                                  # COA API client
  src/hooks/useAP.ts                             # COA query fix
  src/app/dashboard/document/[id]/ap-processing/page.tsx # duplicate back link removed
```
