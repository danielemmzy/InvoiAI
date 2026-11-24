# Production Repair Plan — 2026-11-17

Supabase project: `lyjvctomtlqqqivjjrzc` (InvoiAI production).

Companion file: **`PRODUCTION_REPAIR_20261117.sql`** (repository root). That file is the
executable artefact for exactly four repairs; this document is the ordering rationale,
the affected code paths, the evidence, and the decisions that need to be made before it
runs.

Nothing in this plan has been applied. No connection was made to production, no SQL was
executed against production, and no migration was applied, reapplied, or rolled back.
No application code was changed.

**Revision 2** of the SQL file hardened it for review: no `CREATE OR REPLACE FUNCTION` and
no `DROP POLICY`, existing functions/policies/indexes are inspected and compared instead of
overwritten, the draft table's structure is asserted column by column, both `SECURITY
DEFINER` functions pin `search_path = public, pg_temp`, and the privilege narrowing on
`ap_email_intake_addresses` only happens after its RLS state and policies are proven. It
also uncovered and corrected a defect in the repo's Ticket 10 pair (decision D9).

---

## 1. Scope

Four repairs only, all additive:

| # | Repair | Missing production object |
|---|---|---|
| 1 | Coding reasoning | `public.invoice_codings.reasoning` |
| 2 | Resumable onboarding | `public.onboarding_drafts`, `public.claim_onboarding_workspace(uuid)`, `organizations.business_type` / `monthly_invoice_volume` / `accounting_software` |
| 3 | AP email rotation | `public.manage_ap_email_intake_address(uuid, uuid, text, boolean)` + the two partial unique indexes it depends on |
| 4 | Document bucket policy | `storage.buckets` row `documents`: private, 10 MiB, MIME allowlist |

`PRODUCTION_REPAIR_20261117.sql` lives at the repository root on purpose, not in
`backend/migrations/`: `scripts/check_migration_parity.py` and
`backend/tests/test_migration_parity.py` require every `\d{8}_[A-Za-z0-9_]+\.sql` file in
`backend/migrations` to be registered in `backend/schema.sql`, and this repair must not
touch `schema.sql`. Once these objects are added to the migration history and
`schema.sql` (a separate, reviewable change), this script can be retired.

### Safety properties of the SQL file

* Additive only: no `DROP`, no `RENAME`, no type change, no data `UPDATE` other than the
  `storage.buckets` settings row for `documents`.
* Every section checks its own preconditions and `RAISE`s **before** writing when
  production does not match the assumption.
* All sections run inside one explicit transaction with `set local lock_timeout = '5s'`,
  so a guard failure or a busy table rolls back everything rather than half-applying.
* Idempotent: a second run is a no-op (verified — see §8).
* A repair is only "complete" when its column in the Section 6 summary (V9) reads true.

---

## 2. Evidence base and its limits

Evidence used (all read-only):

* Cached PostgREST OpenAPI snapshot of the production project,
  `$TMP/invoiai_prod_openapi.json` (1,002,002 bytes, captured 2026-11-17). This exposes
  the `public` schema's tables, views, columns, `required` (NOT NULL) lists, and the
  callable `/rpc/*` set.
* Every migration in `backend/migrations/` and the application call sites listed in §4.

What the snapshot establishes:

| Fact | Value |
|---|---|
| `invoice_codings` columns | every model column except `reasoning` |
| `organizations` columns | no `business_type`, `monthly_invoice_volume`, `accounting_software` |
| `onboarding_drafts` | absent (no path, no definition) |
| `claim_onboarding_workspace` | absent from `/rpc/*` |
| `ap_email_intake_addresses` | present, exactly `(id, org_id, email_address, is_active, created_by, created_at)`; only `created_at, email_address, id, is_active, org_id` are NOT NULL |
| `manage_ap_email_intake_address` | absent from `/rpc/*` |
| `documents` bucket | exists; `file_size_limit` and `allowed_mime_types` were never applied |

What the snapshot **cannot** show, and therefore what is not asserted anywhere in the SQL
file: index definitions, `relrowsecurity`, policy text, trigger definitions, function
bodies, `prosecdef` / `proconfig` of existing functions, table grants, and the contents of
`supabase_migrations.schema_migrations` (PostgREST returns `406 PGRST106` because only
`public` and `graphql_public` are exposed). §6 gives the exact SQL to close each of those
gaps from a real connection.

One further divergence found while checking the snapshot, relevant to §5: production
already exposes `/rpc/save_purchase_order_with_lines`, `/rpc/create_goods_receipt_atomic`,
`/rpc/void_goods_receipt_atomic`, and `/rpc/replace_document_match_allocations`, none of
which are defined by any file in `backend/migrations/`, and it exposes
`/purchase_order_line_balances` as a **view** with 16 columns.

---

## 3. Implementation order

Order is by risk and by what unblocks the most user-facing behaviour; there is no
inter-repair dependency except the shared transaction and the final schema reload.

| Step | Action | Depends on | Reversible |
|---|---|---|---|
| 0 | Take a database backup / PITR bookmark; run Section 0 preflight and archive its output | — | — |
| 1 | Repair 1 — `invoice_codings.reasoning` | Step 0 | drop column (loses data) |
| 2 | Repair 2 — `organizations` columns → `onboarding_drafts` (+ index, RLS, policy) → `claim_onboarding_workspace` → grants | Step 1 (same transaction) | drop table/column/function |
| 3 | Repair 3 — the two partial unique indexes, then `manage_ap_email_intake_address` | Step 2 (same transaction) | drop function/index |
| 4 | Repair 4 — `storage.buckets` row `documents` | Step 3 (same transaction) | set settings back to NULL |
| 5 | `commit;` then `notify pgrst, 'reload schema';` | Step 4 | — |
| 6 | Section 6 verification V1–V9; the four booleans in V9 must all be true | Step 5 | — |
| 7 | Deploy nothing. Application code already expects these objects; no feature flag or env change is needed | Step 6 | — |

Within Repair 2 the internal order matters and is already encoded in the SQL file:
`organizations` columns first (the RPC reads them), then the draft table, then its unique
index, RLS and owner policy, then the function, then the grants.

Run steps 1–5 as a single script execution. Do not run them section by section: the
`begin;` … `commit;` wrapper is the only thing that makes a mid-way guard failure safe.

Do not run the file while another session holds a long transaction on
`public.organizations` or `public.invoice_codings`; `lock_timeout = '5s'` will abort and
roll back instead of queueing behind it.

### Timing and locking expectations

* `alter table ... add column if not exists` on `organizations` (3 columns) and
  `invoice_codings` (1 column) takes an `ACCESS EXCLUSIVE` lock for a metadata-only
  change. Sub-second on tables of this size; the 5 s `lock_timeout` is the safety valve.
* `create table onboarding_drafts` and `create function` take no lock on existing data.
* `create unique index` (not `concurrently`) on `ap_email_intake_addresses` takes a
  `SHARE` lock; the table is small (one active address per organization). Building it
  concurrently inside the transaction is impossible (`CREATE INDEX CONCURRENTLY` cannot
  run in a transaction block), which is why the preflight duplicate counts in §4.3 must be
  zero before running.
* `update storage.buckets` affects one row.

---

## 4. Repair detail

### 4.1 Repair 1 — `public.invoice_codings.reasoning`

*Finding.* The column is absent from production. Every path in
`backend/app/services/ap/gl_coding_service.py` (lines 184, 204, 211, 212) constructs an
`InvoiceCoding` with a non-null `reasoning`, `backend/app/models/domain/ap.py:77` declares
it, and `backend/app/mappers/ap/coding_mapper.py:7-10` serialises the model with
`exclude_none=True` — so a live insert always carries `reasoning`. PostgREST rejects the
write with `PGRST204` ("column not found in schema cache"), i.e. **automated GL coding
fails on production today**.

*Change.* `alter table public.invoice_codings add column if not exists reasoning text;`
Text, nullable, no default, no backfill. Existing rows read `NULL`, which the model already
allows (`str | None = None`).

*Not affected.* No index, no constraint, no RLS change. No code change.

*Verification.* V1 (`reasoning | text | YES`), V9 `repair_1_reasoning = true`.

*Rollback.* `alter table public.invoice_codings drop column reasoning;` — destroys written
reasoning, so only if the code path is rolled back first.

### 4.2 Repair 2 — resumable onboarding

*Finding.* Three separate gaps, all in the onboarding flow:

1. `public.onboarding_drafts` is absent. `backend/app/repositories/organization/onboarding_draft_repository.py`
   reads (`:19`), upserts (`:26`) and updates (`:66`) that table. Both
   `GET /onboarding/draft` and `PUT /onboarding/draft` in `backend/app/routers/onboarding.py`
   therefore fail.
2. `public.claim_onboarding_workspace(uuid)` is absent, but
   `onboarding_draft_repository.py:51-59` calls it via `rpc("claim_onboarding_workspace",
   {"p_user_id": ...})` with no fallback. `backend/app/services/organization_service.py:101`
   calls that on every `POST /onboarding/complete` (`organization_service.py:81-112`).
3. `organizations.business_type`, `monthly_invoice_volume`, `accounting_software` are
   absent, but `create_workspace` writes them unconditionally
   (`organization_service.py:502-504`, fed from `:106-108`). The insert fails with
   `PGRST204` even if the draft table and RPC exist.

Net effect: **a new user cannot complete onboarding on production.** This repair is the
highest-value of the four.

*Change* (all idempotent, guarded):

* `onboarding_drafts` with `id`, `user_id` (unique, FK to `auth.users`), `step`, `data`
  (jsonb), `completed`, `workspace_id`, `created_at`, `updated_at` — the shape the
  repository reads and writes.
* Unique constraint/index on `user_id` (the upsert's `on_conflict` target), plus
  `idx_onboarding_drafts_user`.
* `workspace_id` is plain `uuid` with **no foreign key** to `organizations`, although both
  repo migrations declare one. `organization_service.complete_onboarding` claims the id
  (`:101`) and only then creates the organization (`:102`), so the declared FK makes the
  first claim fail with a foreign key violation — reproduced in the Postgres harness. The
  column holds a pre-commitment value, not a live reference; a deleted workspace is already
  handled in code (`:83-92`, lookup returns `None` → 409). Decision D9.
* `alter table ... enable row level security` + the owner policy
  `onboarding_drafts_owner` (the repository uses the service role, so the policy is
  defence in depth, not the load-bearing path). The policy is **never dropped**: if it
  already exists its command, permissiveness, roles, `USING` and `WITH CHECK` are compared
  with `(auth.uid() = user_id)` and any difference stops the script; any other policy on
  the table also stops it.
* The draft table's structure is asserted before and after creation (8 columns with exact
  types, nullability and defaults, no extra columns, PK on `id`, unique on `user_id`,
  `user_id` FK with `on delete cascade`, the `step` CHECK, and the absence of a
  `workspace_id` FK).
* The three `organizations` columns as nullable `text`. They must be `text`, not enums:
  `backend/app/schemas/onboarding.py` validates the values with `Literal` types
  (`BusinessType`, `AccountingSoftware`, `InvoiceVolume`) before they reach the database,
  and `NULL` is legitimate for non-business workspaces (`organization_service.py:502-504`).
* `claim_onboarding_workspace(p_user_id uuid) returns uuid`, `security definer`,
  `set search_path = public, pg_temp` with the one table reference schema-qualified
  (decision D8). It reserves one stable workspace id per user so a retried
  `POST /onboarding/complete` does not create two organizations; it is idempotent for an
  already-claimed draft. It is created only when absent: an existing function is compared
  on return type, `security definer`, language, `proconfig` and normalised body, and is
  either accepted untouched or the script stops. No body is ever replaced, and no second
  overload is created.
* `revoke all on function ... from public, anon, authenticated;`
  `grant execute ... to service_role;` — the backend is the only caller. Roles are checked
  in `pg_roles` before being named in the statement.

*Verification.* V2 (8 columns with exact types/nullability/defaults), V2b (constraints:
PK, unique `user_id`, one FK, the `step` CHECK, no `workspace_id` FK), V2c (RLS on, exactly
one policy, `FOR ALL`, permissive, roles `{0}`, both expressions `auth.uid() = user_id`),
V2d (unique index on `user_id` alone + `idx_onboarding_drafts_user`), V3 (three
`text`/nullable columns), V4/V5 (function identity, `security definer`, `proconfig =
search_path=public, pg_temp`, `service_role` can execute, `anon` cannot), V9 gate.

*Functional check after apply* (from a real session, with a throwaway user): `GET
/onboarding/draft` returns `{}`, `PUT /onboarding/draft` persists a step, and `POST
/onboarding/complete` twice with the same payload returns the same workspace id.

*Rollback.* Revoke from `service_role`, drop the function, drop the policy, disable RLS,
drop the index, drop the table (**destroys in-progress drafts**), drop the three columns
(**destroys the collected profile answers**). Order matters: function before table.

### 4.3 Repair 3 — `public.manage_ap_email_intake_address(...)`

*Finding.* The RPC is absent, but `backend/app/services/ap/email_address_service.py:12-16`
calls it whenever an organization reads or rotates its intake address, and raises if no
rows come back. The table itself exists with exactly the six columns the function writes.

The function's rotation branch makes "one active address per organization" and "one active
address value across the platform" invariants that only hold if the two partial unique
indexes exist, so the indexes are part of this repair and are created **before** the
function.

*Change.*

* `uq_ap_email_address_one_active_per_org` — `unique (org_id) where is_active is true`.
* `uq_ap_email_address_unique_active_value` — `unique (lower(email_address)) where
  is_active is true`.
* Both are **verified, not `if not exists`**: a same-named relation must be an index on
  this table, unique, exactly one key column, with key expression `org_id` /
  `lower(email_address)`, predicate `is_active IS TRUE`, and valid+ready. Anything else
  stops the script and prints `pg_get_indexdef`. A pre-existing relation of another kind
  with that name also stops it.
* `manage_ap_email_intake_address(p_org_id uuid, p_created_by uuid, p_email_address text,
  p_rotate boolean)` returning `setof public.ap_email_intake_addresses`, `security definer`,
  `set search_path = public, pg_temp`. Rotating deactivates the current row and inserts a
  new derived address; the preflight in Section 0.3 and the guard inside Section 3 both
  refuse to run when duplicate active rows already exist, because `create unique index`
  would fail after the table had been partially touched.
* Grants: `revoke all ... from public, anon, authenticated`, `grant execute ... to
  service_role`, and the same on the table's DML privileges — but the table's privileges
  are narrowed only after inspection: the script refuses to run if *any* policy exists on
  `ap_email_intake_addresses`, enables RLS first, reports the effective privileges it found
  (`has_table_privilege`, which includes what `PUBLIC` confers) via `RAISE NOTICE`, then
  revokes and re-checks that `service_role` kept SELECT/INSERT/UPDATE/DELETE. Justification
  for narrowing a pre-existing table: every read/write goes through the service-role
  client (`app/core/supabase.py:44-56`, `routers/ap.py:931`,
  `services/ap/email_intake_service.py:51`); there is no anon/authenticated call path.
* The function is created only when absent: an existing overload with a different signature
  stops the script, and an existing identical one is compared (return type, `setof`,
  `security definer`, plpgsql, one defaulted argument, `proconfig`, normalised body) and
  left untouched.

*Decision required:* D2 in §7 (whether "one active address per organization" is the
product rule). The index names are new, so no production object is overwritten.

*Verification.* V6 (both indexes present, `indisvalid` and `indisready`), V7 (the
invariants hold on live rows: 0 and 0), V4/V5 (function shape and grants), V9
`repair_3_ap_email = true`.

*Rollback.* Drop the function, then the indexes. **Leave the table, its rows and its RLS
state alone** — they predate this repair.

### 4.4 Repair 4 — private `documents` bucket, 10 MiB, MIME allowlist

*Finding.* `20261109_private_documents_bucket.sql` is PARTIAL: the bucket exists but
`file_size_limit` and `allowed_mime_types` are still unset, so the storage layer accepts
arbitrarily large uploads and any content type. `backend/app/core/config.py:205-215`
declares the intended contract (`documents`, 10 MB, pdf/jpeg/png/webp).

*Change.* One `update storage.buckets` on `id = 'documents'`:
`public = false`, `file_size_limit = 10485760`, and
`allowed_mime_types = {application/pdf, image/jpeg, image/png, image/webp, image/tiff}`.

*Why `image/tiff` is in the list.* It is the one deliberate divergence from
`20261109_private_documents_bucket.sql` (five types instead of four) and from
`config.allowed_file_types` (which lists pdf/jpeg/png/webp). Reason:
`backend/app/services/ap/email_intake_service.py:20` has
`ALLOWED_TYPES = {application/pdf, image/png, image/jpeg, image/tiff}` and uploads accepted
attachments through this same bucket. A bucket allowlist without TIFF would break AP email
intake for scanned invoices while leaving the code's own allowlist unchanged. This is
decision **D1**; if product wants TIFF rejected, the correct change is in
`email_intake_service.py`, not silently in the bucket.

*Why making the bucket private is safe for the app.* The only read path is
`create_signed_url` (`backend/app/services/storage/storage.py:226-263`, called from
`backend/app/routers/documents.py:714`). There is no `get_public_url` and no
`/storage/v1/object/public/` URL anywhere in `backend/app` or `frontend/src`, so no surface
depends on public object URLs.

*Verification.* V8 (one row; `bucket_is_public = false`; `file_size_limit = 10485760`;
allowlist covers the five types and has no extras), V9 `repair_4_bucket = true`.

*Rollback.*

```sql
update storage.buckets
   set file_size_limit = null, allowed_mime_types = null, public = false
 where id = 'documents';
```

`public = false` is preserved even on rollback: a public bucket was never a valid state for
this project.

*Post-apply functional check:* upload a >10 MiB PDF (expect rejection from the storage API),
upload a `.docx` (expect rejection), upload a PDF (expect success), then open it in the UI
(expect a signed URL to work).

---

## 5. Deliberately not included, and why

### 5.1 Ticket 21 / 22 purchase-order and allocation migrations

Not included, and they must **not** be applied as-is:

* `20261110_purchase_order_00_org_number.sql` — `purchase_orders.org_number` is genuinely
  absent, but this file does more than add the column: it adds
  `purchase_order_number_counters` and a `assign_purchase_order_org_number()` trigger. The
  application writes `po_number` directly (`backend/app/routers/ap.py` ~285-325) and never
  reads `org_number`; adding a trigger that rewrites numbering on a table the app writes
  directly is a behaviour change, not a repair.
* `20261110_purchase_order_lines_and_atomic_receipts.sql` — production's
  `purchase_order_lines` has 14 columns (`quantity_ordered`, `line_amount`, `metadata`, …)
  and no `line_number` / `quantity` / `amount`; the migration adds the second set. The app
  writes the production shape directly. Accepting the migration would leave two
  overlapping line schemas in one table.
* `20261111_document_match_allocations.sql` — the migration ends with
  `create or replace function public.purchase_order_line_balances(uuid, uuid)`, while
  production exposes **`/purchase_order_line_balances` as a view** (16 columns including
  `received_quantity` and `remaining_quantity`). Creating a function of that name next to
  the view creates two objects with one name and changes what `select ... from
  purchase_order_line_balances(...)` means.
  Production also already has `/rpc/replace_document_match_allocations`, which no file in
  this repository defines — the live allocation design comes from outside this repo's
  migration lineage.

Conclusion: production already runs a different PO/receipt/allocation design, and re-running
these files would overwrite live function bodies (forbidden) and introduce a second
allocation authority. The correct next step is a reconciliation decision, not a repair — see
D4 and the check SQL in §6.5.

### 5.2 `20261012_tenant_isolation_rls_and_audit_indexes.sql`

A 47-table RLS + index sweep. Its current production state cannot be verified read-only
(needs `pg_policies` / `pg_indexes`, §6.1-6.2), and re-asserting it blind could tighten
policies that the running application depends on, or recreate indexes that already exist
under different names. Check-only SQL supplied; no repair.

### 5.3 `20260927_document_type_intake_recognition.sql`

It is a single `UPDATE public.documents` — data correction, not schema. Running it is a
product decision about historical rows; it does not belong in a schema repair. State check
in §6.6.

### 5.4 `20261109_ap_email_intake_rate_limit.sql`

Two `create index if not exists` statements on `ap_email_intake_events`. Real but unrelated
to the four named repairs; they are also cheap to verify (§6.4) and can be added to a later
batch.

### 5.5 Member invitation RPCs (`20261111_atomic_member_seat_capacity.sql`)

Not one of the four repairs, and it needs one more fact than the snapshot exposes.

What the snapshot shows: production has no `create_org_member_invitation` /
`accept_org_member_invitation` RPC (no `/rpc/*` path, no definition), so the functions are
absent. It also shows `org_members` **already has** the invitation columns
(`invite_email`, `invite_token`, `invite_expires_at`, `invited_by`, `joined_at`,
`deactivated_at`, `deactivated_by`) and that `user_id` and `is_active` are nullable. The
migration's two functions only read/write columns that exist and tolerate NULLs, so the
column shape is compatible.

What blocks including it: (a) the seat-capacity semantics — `p_seat_limit` is passed by the
caller, and nothing in the snapshot proves which plan/seat source production uses; (b)
whether existing pending invitations would trip `INVITATION_ALREADY_EXISTS`; (c) it is out
of the requested four-repair scope. Preflight SQL in §6.7. Recommended: a separate,
smaller repair after this one, with the duplicate-invitation count in hand.

---

## 6. Checks that require a real connection (not run)

All read-only. Run in the Supabase SQL editor or via `psql` against production. None of
these is part of `PRODUCTION_REPAIR_20261117.sql` because none is needed to apply it —
they close the evidence gaps listed in §2.

### 6.1 Index inventory (whole `public` schema)

```sql
select schemaname, tablename, indexname, indexdef
  from pg_indexes
 where schemaname = 'public'
 order by tablename, indexname;
```

### 6.2 RLS state and policy inventory

```sql
select c.relname as table_name,
       c.relrowsecurity as rls_enabled,
       c.relforcerowsecurity as rls_forced
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public'
   and c.relkind = 'r'
 order by c.relname;

select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
  from pg_policies
 where schemaname in ('public', 'storage')
 order by schemaname, tablename, policyname;
```

### 6.3 Triggers

```sql
select event_object_schema, event_object_table, trigger_name,
       action_timing, event_manipulation, action_statement
  from information_schema.triggers
 where trigger_schema = 'public'
 order by event_object_table, trigger_name;
```

### 6.4 Grants and existing function bodies

```sql
-- table/sequence grants, including the default PUBLIC grants Supabase expects to be revoked
select table_schema, table_name, grantee, privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public'
   and grantee in ('anon', 'authenticated', 'service_role', 'PUBLIC')
 order by table_name, grantee, privilege_type;

-- every public function, its security posture and pinned search_path
select p.oid::regprocedure            as signature,
       p.prosecdef                    as security_definer,
       array_to_string(p.proconfig, ', ') as proconfig
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public'
 order by 1;

-- the two indexes from §5.4, if applied
select indexname, indexdef from pg_indexes
 where schemaname = 'public'
   and indexname in ('idx_ap_email_intake_events_org_created',
                     'idx_ap_email_intake_events_org_sender_created');
```

### 6.5 Migration ledger and the PO/allocation divergence

```sql
-- Not reachable through PostgREST (406 PGRST106); SQL editor / psql only.
select version, name
  from supabase_migrations.schema_migrations
 order by version desc
 limit 60;
```

```sql
-- Production's PO objects. Compare against the three Ticket 21/22 migrations.
select c.relname, c.relkind
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public'
   and c.relname in ('purchase_orders', 'purchase_order_lines',
                     'purchase_order_line_balances', 'document_match_allocations',
                     'document_purchase_order_allocations',
                     'document_po_line_allocations',
                     'document_receipt_line_allocations',
                     'purchase_order_number_counters');
-- expect purchase_order_line_balances to be relkind = 'v' (view), which is exactly why
-- 20261111_document_match_allocations.sql must not be applied as written.

select p.oid::regprocedure, p.prosecdef, array_to_string(p.proconfig, ', ')
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public'
   and p.proname in ('save_purchase_order_with_lines', 'create_goods_receipt_atomic',
                     'void_goods_receipt_atomic', 'replace_document_match_allocations');
-- expect 4 rows (they are already callable in production) and no repo migration that
-- defines them; treat those bodies as authoritative until reconciled.
```

```sql
-- Does production carry the columns the app writes, or the ones the migrations add?
select table_name, column_name, data_type
  from information_schema.columns
 where table_schema = 'public'
   and table_name in ('purchase_orders', 'purchase_order_lines')
 order by table_name, ordinal_position;
```

### 6.6 `20260927` data-correction state

```sql
select count(*) as still_miscategorised
  from public.documents
 where source = 'manual'
   and document_type = 'invoice'
   and (lower(coalesce(file_name, '')) ~ 'purchase[ _-]*order'
        or lower(coalesce(document_number, '')) ~ '^p\.?o\.?[ _#.:/-]*[0-9]+');
-- 0 = already applied or nothing to correct.
```

### 6.7 Member invitations

```sql
select p.oid::regprocedure
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public'
   and p.proname in ('create_org_member_invitation', 'accept_org_member_invitation',
                     'resend_org_member_invitation', 'revoke_org_member_invitation');
-- expect 0 rows (snapshot shows none exposed).

-- what the seat-capacity functions would trip over today
select org_id, count(*) as pending_invitations,
       count(*) filter (where invite_expires_at is not null
                          and invite_expires_at <= now()) as expired
  from public.org_members
 where is_active is false
   and invite_token is not null
 group by org_id
 order by pending_invitations desc;
```

### 6.8 Storage RLS and object count (prerequisite for Repair 4 behaviour)

```sql
select id, name, public, file_size_limit, allowed_mime_types from storage.buckets order by id;

select policyname, cmd, roles, qual, with_check
  from pg_policies
 where schemaname = 'storage' and tablename = 'objects'
 order by policyname;

select bucket_id, count(*) from storage.objects group by bucket_id order by 1;
```

The app reaches objects with the service role + signed URLs, so object policies matter less
than the bucket flags — but confirm no `storage.objects` policy was written assuming a
public bucket before flipping `public` to false.

---

## 7. Conflicts requiring a decision

| ID | Decision | Default in the SQL file | If you choose otherwise |
|---|---|---|---|
| **D1** | Is `image/tiff` allowed in the `documents` bucket? | Yes — `email_intake_service.py:20` accepts TIFF and uploads to this bucket; dropping it would break scanned-invoice intake | Remove TIFF from the bucket allowlist **and** from `ALLOWED_TYPES` in the same change; otherwise intake fails at upload time with a storage error rather than a clear validation error |
| **D2** | Is "one active intake address per organization" correct? | Enforced by `uq_ap_email_address_one_active_per_org`; the rotation RPC deactivates the previous row | If multiple simultaneous addresses per org is a requirement, drop that index from Section 3 and revisit the RPC's rotation branch — but then `email_address_service` must stop assuming a single row |
| **D3** | Seat capacity source for invitations (`p_seat_limit`) — plan, subscription, or `organizations.document_limit`-style column? | Not addressed; invitation repair deferred (§5.5) | Answer needed before the follow-up repair; wrong source means the RPC enforces the wrong cap |
| **D4** | PO/allocation authority: production's view + externally-defined RPCs, or the repo's Ticket 21/22 functions? | Production stays authoritative; Ticket 21/22 not applied | Reconciling means editing the app's PO/receipt writes in `backend/app/routers/ap.py` and rewriting `docs/database/ticket-21-22-migration-package/`, then regenerating that package — a separate, larger change |
| **D5** | Did `20261012`'s RLS sweep already run, and under which policy names? | Untouched; §6.2 tells you | If gaps are found, they need their own per-table repair with the indexes actually present |
| **D6** | Should `20260927`'s historical `document_type` correction run? | No — data, not schema | Run `§6.6`; if the count is non-zero, schedule the `UPDATE` with the product owner |
| **D7** | Are the two `ap_email_intake_events` indexes wanted now? | No — §5.4 | Add as a small separate batch (they are `if not exists`, so trivially idempotent) |
| **D8** | `search_path` for `claim_onboarding_workspace`: `public` (as the migration ships it) vs `public, pg_temp` | `set search_path = public, pg_temp`, both functions, with schema-qualified body references | Reverting to `public` only is possible but `20261109_resumable_business_onboarding.sql` would then reintroduce the weaker body if ever applied — update that migration too |
| **D9** | Should `onboarding_drafts.workspace_id` keep the `references public.organizations(id) on delete set null` that both repo migrations declare? | **No** — the FK is omitted. `complete_onboarding` claims the id (`organization_service.py:101`) before creating the organization (`:102`), so the FK aborts every first claim (reproduced: `insert or update ... violates foreign key constraint`) | If the FK is required for integrity, the claim must stop writing `workspace_id` and the reservation has to live somewhere that survives `save()` overwriting `data`; that is an application change, not a schema repair |

---

## 8. Verification performed on the SQL file (local, not production)

The file was executed end to end against a throwaway `postgres:16` container, not against
production:

* Stubs recreated the parts of production the script touches: roles `anon`,
  `authenticated`, `service_role`; schemas `auth` (with `auth.users`, `auth.uid()`) and
  `storage` (`storage.buckets` containing one row for `documents`); `public.organizations`,
  `public.invoice_codings`, `public.ap_email_intake_addresses`, plus one organization and
  one active legacy address row.
* **Run 1** (`psql -v ON_ERROR_STOP=1`): exit 0. Sections 1-5 applied in one transaction,
  commit, then Section 6 returned every expected value:
  `reasoning text NULL`, 8 draft columns, RLS on with one owner policy, 3 organization
  columns, both functions `security definer` with `search_path` pinned and
  `service_role`-only execute, both indexes `indisvalid`/`indisready`, duplicate counts
  0/0, bucket `is_private = true`, `file_size_limit = 10485760`, allowlist exactly the five
  types, and V9 = four true.
* **Run 2** (same database): exit 0. Every guard reported the object it found and left it
  untouched (`policy … already matches`, `index … already exists with the expected
  definition`, `function … already exists with the expected definition`); no object was
  created, replaced or dropped.
* **Eight negative databases**, each seeded with exactly one conflicting condition, all
  stopped with the intended message before committing:
  1. duplicate active addresses → `DATA CONFLICT: an organization has more than one active
     AP email address…`
  2. pre-existing `claim_onboarding_workspace` with a different body → `CONFLICT … WITHOUT
     security definer`, body left untouched (verified afterwards: `prosrc` unchanged, no
     `proconfig`)
  3. same index name with `where is_active is false` → `CONFLICT: index … its predicate is
     (is_active IS FALSE)`
  4. an unrelated policy on `ap_email_intake_addresses` → `REVIEW REQUIRED … will not
     narrow privileges under an unknown policy`
  5. pre-existing draft table missing `step` → `CONFLICT … is missing column step`
  6. matching draft table with an extra policy → `CONFLICT … already has other policy(ies)`
  7. bucket row absent → `PREFLIGHT FAILED: bucket "documents" does not exist`
  8. the repo migration's exact draft table (with the `workspace_id` FK) → `CONFLICT … has
     a foreign key on (workspace_id)`, explaining the claim failure and asking for a manual
     decision instead of dropping it
  After each failure a follow-up query confirmed **full rollback** (no `reasoning` column,
  no organization columns, no draft table, no functions/indexes, RLS state unchanged, bucket
  row untouched) and that pre-existing objects were unchanged.
* **Functional check** in the migrated database: `claim_onboarding_workspace` returned the
  same reserved uuid on two consecutive calls; `manage_ap_email_intake_address` returned the
  existing active row on a non-rotating call, and on `p_rotate = true` deactivated the old
  address (lower-cased insert) and returned the new one.
* The scratch container was removed afterwards.

Limitations of that check: it proves syntax, idempotency, guard logic and rollback
semantics, and that the verification queries return the expected shapes. It does **not**
prove production behaviour — production has real data in `ap_email_intake_addresses`, real
`storage.objects` rows, and existing policies/grants that the stubs only approximate. That
is what Section 0 preflight and Section 6 are for, and no repair may be marked complete
until V1-V9 read as expected against production.

---

## 9. Stop point

Everything up to here is a proposal. Before anything runs:

1. Answer D1 (TIFF), D2 (one active address per org) and accept D9 (no `workspace_id` FK) —
   each of the first two changes what the file writes, and D9 changes what the table looks
   like against the migration history.
2. Run Section 0 preflight against production and confirm the five expectations.
3. Decide whether Ticket 21/22 (`D4`) and member invitations (§5.5) get their own follow-up
   plan now, or after this batch.

Then the sequence is: backup → Section 0 → Sections 1-5 → Section 6 → four true values in V9.
