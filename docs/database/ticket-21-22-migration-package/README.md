# Ticket 21/22 migration package

Purchase orders, atomic goods receipts, and line-level invoice match allocations.

Apply these three files to the InvoiAI Supabase project, in this order.

| Order | File |
|---|---|
| 1 | `backend/migrations/20261110_purchase_order_00_org_number.sql` |
| 2 | `backend/migrations/20261110_purchase_order_lines_and_atomic_receipts.sql` |
| 3 | `backend/migrations/20261111_document_match_allocations.sql` |

Order is mandatory: 2 adds lines to the numbering from 1, and 3 references the
receipt structure from 2.

## Before you start

1. Open the correct InvoiAI Supabase project.
2. Take a recent database backup (Dashboard → Database → Backups).
3. Keep the SQL Editor open on that project.

All three migrations are additive and idempotent. Re-running one is a no-op, so
a partial run can be repeated from the top without duplicating anything. Do not
run them twice "just in case" — it costs nothing but tells you nothing either.

## Apply

For each file, in order:

1. Open SQL Editor → New query.
2. Paste the whole file.
3. Run it.
4. Confirm the result is success (no error), then move to the next file.

Every statement is guarded (`if not exists`, `create or replace`, `drop trigger
if exists`), so a legacy table that predates the manifest will not abort the run.

## Verify

Paste `verify.sql` and run it. It is read-only.

- Checks 1–16 return a table. Every row must say `OK`.
- Checks 17–18 are printed as `NOTICE` lines and must also say `OK`.

On an unmigrated database the same script returns `FAIL` for everything without
throwing an error, so it is safe to use as a pre-flight check too.

If a check fails, stop and report which `check_id` failed before running
anything else.

## What each migration changes

### 1. `20261110_purchase_order_00_org_number.sql`

- `purchase_order_number_counters` — one row per organization.
- `next_purchase_order_org_number(uuid)` — returns `PO-000001`, atomically.
- `purchase_orders.org_number` — InvoiAI-assigned per-organization PO number.
- Unique per organization where not null.
- `trg_purchase_orders_org_number` — fills `org_number` on insert when absent.
- Backfills `org_number` for existing POs.

`po_number` is untouched. It stays the provider- or user-supplied number;
`org_number` is the internal reference that exists even with no provider.

### 2. `20261110_purchase_order_lines_and_atomic_receipts.sql`

- `purchase_order_lines` — created only if missing, then every column is added
  with `if not exists`.
- `goods_receipts.voided_at`, `voided_by`, `void_reason`.
- `record_goods_receipt(org, po, receipt, lines)` — header + lines in one
  transaction, idempotent on `(org_id, external_id)`.
- `void_goods_receipt(org, receipt, reason, actor)` — reason required, writes an
  `audit_logs` event.
- Indexes and RLS for the new table and the receipt lookups.

### 3. `20261111_document_match_allocations.sql`

- `document_match_allocations` — the line-level match authority.
- Unique active key per invoice line + PO line + receipt line.
- `enforce_document_match_allocation` trigger — tenancy, ownership, and
  over-allocation of the invoice line, PO line, and receipt line.
- Guards that make an allocated receipt header/line immutable, and that require
  a reason to void.
- `purchase_order_line_balances(org, po)` — ordered / received / allocated /
  remaining quantity and amount.

## Design decisions worth knowing

- **`org_number` is a new column, not a rename.** Nothing in the app read it
  before; the trigger fills it so existing insert paths keep working unchanged.
- **`purchase_order_lines` may already exist.** The migration creates it when
  missing and only adds missing columns otherwise, so a legacy shape does not
  break the run. Columns the app needs are added alongside existing ones.
- **Received quantity is never stored.** It is derived from confirmed,
  non-voided receipt lines in `purchase_order_line_balances`. A cached counter
  would drift from the evidence.
- **Voiding does not rewrite allocations.** A void changes the receipt only; the
  matching service must re-run and record the consequence.
- **The write RPCs are `service_role` only.** They take `p_org_id` from the
  caller, so exposing them to `authenticated` would let a user pass another
  organization's id. The backend already uses the service-role client.
- **`documents.purchase_order_id` / `documents.goods_receipt_id` are kept** as a
  convenience "primary" reference. `document_match_allocations` is the authority.

## Not covered here

These migrations are the database half only. No application code reads the new
structures yet, and the ticket branches that would use them were never written.
Still to do in code:

- wire `PurchaseOrderLines` repository/service and CSV import
- call `record_goods_receipt` / `void_goods_receipt` from the receipts router
- persist and read allocations in `MatchingService`
- add the provider `supports_purchase_orders` capability flag

## Rollback

The migrations only add objects, so rollback is a targeted drop. Do not run this
on a database that already holds allocations or receipts you need:

```sql
drop function if exists public.purchase_order_line_balances(uuid, uuid);
drop trigger if exists trg_goods_receipts_allocated_guard on public.goods_receipts;
drop trigger if exists trg_goods_receipt_lines_allocated_guard on public.goods_receipt_lines;
drop table if exists public.document_match_allocations;
drop function if exists public.void_goods_receipt(uuid, uuid, text, uuid);
drop function if exists public.record_goods_receipt(uuid, uuid, jsonb, jsonb);
alter table public.goods_receipts
    drop column if exists voided_at,
    drop column if exists voided_by,
    drop column if exists void_reason;
-- Leave purchase_order_lines in place if it already existed before migration 2.
drop trigger if exists trg_purchase_orders_org_number on public.purchase_orders;
drop function if exists public.assign_purchase_order_org_number();
alter table public.purchase_orders drop column if exists org_number;
drop table if exists public.purchase_order_lines;
drop function if exists public.next_purchase_order_org_number(uuid);
drop table if exists public.purchase_order_number_counters;
```

## Note on migration history

Running these in the SQL Editor does not insert rows into
`supabase_migrations.schema_migrations`. `scripts/check_migration_parity.py`
will therefore report them as not applied against that project, even though the
schema is correct. That is expected for a manual apply; the manifest check
(`backend/schema.sql`) still passes locally.
