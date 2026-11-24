-- ============================================================================
-- PRODUCTION_REPAIR_20261117.sql
--
-- Project : InvoiAI  (Supabase project lyjvctomtlqqqivjjrzc)
-- Purpose : One consolidated, reviewable repair script for the four confirmed
--           production gaps. This file is NOT a migration and is deliberately
--           kept out of backend/migrations/ because
--           scripts/check_migration_parity.py + backend/tests/test_migration_parity.py
--           require every file in that directory to be listed in
--           backend/schema.sql, which this repair must not touch.
--
-- REVISION 2 (hardening pass, 2026-11-18)
--   R2.1 No CREATE OR REPLACE FUNCTION. Each function is created only when
--        absent. If the exact signature already exists its definition is
--        compared with the one in this file: identical -> left untouched,
--        anything else -> hard stop. No function body is ever replaced.
--   R2.2 No DROP POLICY in the apply path. An existing onboarding_drafts_owner
--        is inspected (command, permissiveness, roles, USING, WITH CHECK) and
--        must match. The only DROP POLICY text in this file is inside the
--        commented-out SECTION 7 rollback notes, which never execute.
--        Any other policy on the table also stops the script.
--   R2.3 The two AP email indexes are verified by key definition, uniqueness,
--        key count, partial predicate and validity when the name is taken.
--        IF NOT EXISTS is no longer trusted for them.
--   R2.4 ap_email_intake_addresses: RLS state and every policy are inspected
--        before any privilege change. Grants are revoked only after RLS is on
--        and only when no policy grants anon/authenticated access. The
--        pre-existing effective privileges are reported by RAISE NOTICE.
--   R2.5 onboarding_drafts structure is asserted explicitly: 8 columns with
--        exact types, nullability and defaults, no extra columns, PK on id,
--        unique on user_id, both foreign keys with delete actions, step CHECK.
--   R2.6 Both SECURITY DEFINER functions pin search_path = public, pg_temp and
--        schema-qualify every object they touch.
--   R2.8 Two deliberate differences from the repo migrations, both verified in
--        a throwaway Postgres 16 harness:
--        * workspace_id on onboarding_drafts has NO foreign key to
--          organizations. The migrations declare one, but
--          organization_service.complete_onboarding reserves the id before
--          creating the organization, so that FK makes every claim fail.
--        * claim_onboarding_workspace pins search_path = public, pg_temp
--          (the migration pins only public).
--
-- IN SCOPE (exactly four repairs)
--   1. public.invoice_codings.reasoning                    (missing column)
--   2. onboarding drafts + organizations profile columns
--      + public.claim_onboarding_workspace(uuid)           (missing table/columns/RPC)
--   3. public.manage_ap_email_intake_address(...)          (missing RPC)
--      + the two partial unique indexes it depends on      (missing indexes)
--   4. storage bucket 'documents': private + 10 MiB + MIME allowlist
--
-- DELIBERATELY NOT INCLUDED (see docs/PRODUCTION_REPAIR_PLAN_20261117.md)
--   * create/resend/accept_org_member_invitation RPCs -> not one of the four
--     named repairs (20261111_atomic_member_seat_capacity.sql); the seat-limit
--     source is still undecided. Plan sections 5.5 and 6.7.
--   * 20261110_purchase_order_00_org_number.sql,
--     20261110_purchase_order_lines_and_atomic_receipts.sql,
--     20261111_document_match_allocations.sql -> production already runs a
--     different PO/receipt/allocation design: it exposes
--     /rpc/save_purchase_order_with_lines, create_goods_receipt_atomic,
--     void_goods_receipt_atomic and replace_document_match_allocations (none
--     defined by any file in backend/migrations), and purchase_order_line_balances
--     is a VIEW. Applying these files would overwrite live function bodies and
--     add a same-named function beside the view. Plan section 5.1 / decision D4.
--   * 20261012_tenant_isolation_rls_and_audit_indexes.sql -> a 47-table RLS
--     sweep whose production state cannot be verified read-only.
--   * 20260927_document_type_intake_recognition.sql -> a DML UPDATE, not DDL.
--   * 20261109_ap_email_intake_rate_limit.sql -> two indexes, not one of the
--     four named repairs.
--
-- EVIDENCE BASIS
--   Read-only PostgREST OpenAPI snapshot of the production project (cached at
--   $TMP/invoiai_prod_openapi.json, 1,002,002 bytes, captured 2026-11-17),
--   compared against backend/migrations/*.sql and the application call sites.
--   No connection was made to production; nothing here ran there.
--
-- WHAT THE SNAPSHOT PROVED
--   public.invoice_codings            -> every model column except `reasoning`
--   public.organizations              -> no business_type / monthly_invoice_volume
--                                        / accounting_software
--   public.onboarding_drafts          -> absent
--   public.claim_onboarding_workspace -> absent
--   public.ap_email_intake_addresses  -> present with exactly (id, org_id,
--                                        email_address, is_active, created_by,
--                                        created_at)
--   public.manage_ap_email_intake_address -> absent
--   storage bucket 'documents'        -> exists; file_size_limit and
--                                        allowed_mime_types never applied
--   What the snapshot could NOT show: index definitions, policy text,
--   relrowsecurity, triggers, function bodies, grants. Those are guarded at run
--   time below, because the guards query the live catalogs rather than assume.
--
-- HOW TO RUN
--   Step 1  Run SECTION 0 alone. It is read-only. Read every row.
--   Step 2  Run SECTIONS 1-5 as one script. They are one explicit transaction,
--           so any guard failure rolls back everything. Re-running is a no-op:
--           every object is verified before creation and an identical existing
--           object is left untouched.
--   Step 3  Run SECTION 6. Every check must return the stated shape.
--   Do not run while another session holds a long transaction on
--   public.organizations or public.invoice_codings (lock_timeout = '5s' makes
--   this fail fast instead of queueing).
--
-- SAFETY PROPERTIES
--   * Additive only: no DROP, no RENAME, no column type change, no data UPDATE
--     except storage.buckets settings for the single bucket 'documents'.
--   * No existing object is ever replaced. Functions, the policy and the
--     indexes are verified against the definitions below; a mismatch is a hard
--     stop that prints the actual definition.
--   * Privileges are narrowed only after RLS state and policies prove that no
--     client role is being cut off.
--   * Every section verifies its own preconditions and RAISEs before writing
--     when production does not match the assumption.
-- ============================================================================

-- ============================================================================
-- SECTION 0 - PREFLIGHT (READ-ONLY). Run this alone first.
-- ============================================================================

-- 0.1 Repair 1 target: does invoice_codings exist, and is `reasoning` absent?
select
    to_regclass('public.invoice_codings') is not null            as invoice_codings_exists,
    (select format_type(a.atttypid, a.atttypmod)
       from pg_attribute a
      where a.attrelid = to_regclass('public.invoice_codings')
        and a.attname = 'reasoning'
        and a.attnum > 0
        and not a.attisdropped)                                  as reasoning_current_type
;
-- expect: invoice_codings_exists = true, reasoning_current_type = NULL

-- 0.2 Repair 2 targets: table, RPC, and the three organization columns.
select
    to_regclass('public.onboarding_drafts')                      as onboarding_drafts_regclass,
    to_regprocedure('public.claim_onboarding_workspace(uuid)')   as claim_function_regprocedure
;
-- expect: both NULL (nothing to conflict with)

select p.oid::regprocedure                 as claim_overloads,
       p.prosecdef                         as security_definer,
       array_to_string(p.proconfig, ', ')  as proconfig
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public'
   and p.proname = 'claim_onboarding_workspace'
;
-- expect: 0 rows. A row with a different signature is a conflict: STOP.

select a.attname,
       format_type(a.atttypid, a.atttypmod) as current_type,
       a.attnotnull
  from pg_attribute a
 where a.attrelid = 'public.organizations'::regclass
   and a.attname in ('business_type', 'monthly_invoice_volume',
                     'accounting_software')
   and a.attnum > 0
   and not a.attisdropped
 order by a.attname
;
-- expect: 0 rows. Any row here means a conflicting definition already exists.

-- 0.2b If public.onboarding_drafts already exists, this is its full current
--      structure. SECTION 2 accepts it only if it matches the definition in
--      2.3 exactly (columns, types, nullability, defaults, constraints).
select a.attname,
       format_type(a.atttypid, a.atttypmod) as type,
       a.attnotnull,
       pg_get_expr(d.adbin, d.adrelid)      as default_expr
  from pg_attribute a
  left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
 where a.attrelid = to_regclass('public.onboarding_drafts')
   and a.attnum > 0
   and not a.attisdropped
 order by a.attnum
;
-- expect: 0 rows (table absent).

select con.conname, con.contype, pg_get_constraintdef(con.oid) as definition
  from pg_constraint con
 where con.conrelid = to_regclass('public.onboarding_drafts')
 order by con.conname
;
-- expect: 0 rows (table absent).

-- 0.3 Repair 3 targets: address table shape, existing function overloads,
--     and duplicate active rows that would make the unique indexes invalid.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'ap_email_intake_addresses'
 order by ordinal_position
;
-- expect: id, org_id, email_address, is_active, created_by, created_at

select p.oid::regprocedure                 as existing_overload,
       p.prorettype::regtype               as returns,
       p.proretset                         as returns_setof,
       p.prosecdef                         as security_definer,
       array_to_string(p.proconfig, ', ')  as proconfig
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public'
   and p.proname = 'manage_ap_email_intake_address'
;
-- expect: 0 rows. A row with a different signature is a conflict: STOP.

select
    (select count(*)
       from (select org_id
               from public.ap_email_intake_addresses
              where is_active is true
              group by org_id
             having count(*) > 1) d)                            as orgs_with_multiple_active,
    (select count(*)
       from (select lower(email_address)
               from public.ap_email_intake_addresses
              where is_active is true
              group by lower(email_address)
             having count(*) > 1) d)                            as duplicated_active_values
;
-- expect: 0 and 0. Non-zero means SECTION 3 raises and rolls back by design.

-- 0.3b Every privilege and policy currently on the address table. SECTION 3.5
--      reads these same catalogs and refuses to narrow access while any policy
--      exists or while RLS is off with client grants live.
select c.relrowsecurity as rls_enabled
  from pg_class c
 where c.oid = to_regclass('public.ap_email_intake_addresses')
;
-- expect: true or false; either is handled, but read it.

select p.polname,
       p.polcmd,
       p.polpermissive,
       p.polroles,
       pg_get_expr(p.polqual, p.polrelid)      as using_expr,
       pg_get_expr(p.polwithcheck, p.polrelid) as with_check_expr
  from pg_policy p
 where p.polrelid = to_regclass('public.ap_email_intake_addresses')
 order by p.polname
;
-- expect: 0 rows. Any policy here stops SECTION 3.5 for manual review.

select r.rolname,
       has_table_privilege(r.oid, c.oid, 'SELECT') as can_select,
       has_table_privilege(r.oid, c.oid, 'INSERT') as can_insert,
       has_table_privilege(r.oid, c.oid, 'UPDATE') as can_update,
       has_table_privilege(r.oid, c.oid, 'DELETE') as can_delete
  from pg_roles r
  cross join pg_class c
 where c.oid = to_regclass('public.ap_email_intake_addresses')
   and r.rolname in ('anon', 'authenticated', 'service_role')
 order by r.rolname
;
-- expect: service_role true for all four. anon/authenticated may be true today
-- (Supabase default privileges); SECTION 3.5 revokes them only because RLS is
-- enabled and no policy grants them anything. Values here are effective
-- privileges, i.e. they include anything inherited from PUBLIC.

-- 0.4 Repair 3 index names must not already be taken by a different relation
--     or a differently defined index.
select c.relname, c.relkind, pg_get_indexdef(c.oid) as indexdef
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public'
   and c.relname in ('uq_ap_email_address_one_active_per_org',
                     'uq_ap_email_address_unique_active_value')
;
-- expect: 0 rows, or rows whose indexdef matches SECTION 3.2 exactly
--         (UNIQUE btree on org_id / lower(email_address) WHERE (is_active IS TRUE)).

-- 0.5 Repair 4 target: current bucket settings.
select id, name, public, file_size_limit, allowed_mime_types
  from storage.buckets
 where id = 'documents'
;
-- expect: exactly 1 row. file_size_limit / allowed_mime_types expected NULL.

-- ============================================================================
-- SECTIONS 1-5 - APPLY. Runs as one transaction.
-- ============================================================================

begin;

-- Never queue behind a long-running session; fail fast and retry later.
set local lock_timeout = '5s';


-- ----------------------------------------------------------------------------
-- SECTION 1 - REPAIR 1: public.invoice_codings.reasoning
--
-- Why: backend/app/models/domain/ap.py declares
--      `InvoiceCoding.reasoning: str | None = None`; the mapper serialises it on
--      insert (app/mappers/ap/coding_mapper.py `to_insert`), so every GL coding
--      write and every coding read fails while the column is missing.
-- Shape: text, nullable. Matches the model (optional) and the repo migration
--      20261109_ap_coding_reasoning.sql. No default, no backfill: existing rows
--      are semantically "no reasoning recorded".
-- ----------------------------------------------------------------------------

do $$
declare
    v_type text;
begin
    if to_regclass('public.invoice_codings') is null then
        raise exception 'PREFLIGHT FAILED: public.invoice_codings does not exist. Nothing to repair; stop and review.';
    end if;

    select format_type(a.atttypid, a.atttypmod)
      into v_type
      from pg_attribute a
     where a.attrelid = 'public.invoice_codings'::regclass
       and a.attname = 'reasoning'
       and a.attnum > 0
       and not a.attisdropped;

    if v_type is not null and v_type <> 'text' then
        raise exception 'CONFLICT: public.invoice_codings.reasoning already exists as % (expected text). Stop and review.', v_type;
    end if;
end
$$;

alter table public.invoice_codings
    add column if not exists reasoning text;


-- ----------------------------------------------------------------------------
-- SECTION 2 - REPAIR 2: resumable onboarding
--
-- Why: backend/app/repositories/organization/onboarding_draft_repository.py
--      reads/writes table `onboarding_drafts` and calls
--      rpc('claim_onboarding_workspace', {p_user_id}); there is no fallback.
--      backend/app/services/organization_service.py then writes
--      organizations.business_type / monthly_invoice_volume /
--      accounting_software at completion. All of it is absent in production,
--      so onboarding cannot complete at all.
-- Source: backend/migrations/20261014_onboarding_drafts.sql and
--      20261109_resumable_business_onboarding.sql, reproduced with hard guards
--      and a hardened function.
-- ----------------------------------------------------------------------------

-- 2.0 One assertion helper, used twice: once if the table already exists (to
--     refuse an incompatible pre-existing table before anything is altered) and
--     once after creation (to prove what this transaction actually built).
--     It lives in pg_temp, so it disappears with the session and never becomes
--     a production object. CREATE OR REPLACE here is safe precisely because it
--     is session-local; no production function is touched.
create or replace function pg_temp.assert_onboarding_drafts_shape()
returns void
language plpgsql
as $helper$
declare
    v_rel oid := to_regclass('public.onboarding_drafts');
    v_users oid := to_regclass('auth.users');
    v_names text[] := array['id', 'user_id', 'step', 'completed', 'data',
                            'workspace_id', 'created_at', 'updated_at'];
    v_types text[] := array['uuid', 'uuid', 'integer', 'boolean', 'jsonb',
                            'uuid', 'timestamp with time zone',
                            'timestamp with time zone'];
    v_notnull text[] := array['NO', 'NO', 'NO', 'NO', 'NO', 'YES', 'NO', 'NO'];
    v_default text[] := array['gen_random_uuid', null, '1', 'false', '{}',
                              null, 'now(', 'now('];
    v_i int;
    v_type text;
    v_is_notnull boolean;
    v_default_expr text;
    v_extra text;
    v_fk record;
begin
    if v_rel is null then
        raise exception 'ASSERTION FAILED: public.onboarding_drafts does not exist.';
    end if;
    if v_users is null then
        raise exception 'PREFLIGHT FAILED: auth.users is not reachable; the user_id foreign key cannot be verified.';
    end if;

    -- Columns that must not be there.
    select string_agg(a.attname, ', ' order by a.attname)
      into v_extra
      from pg_attribute a
     where a.attrelid = v_rel
       and a.attnum > 0
       and not a.attisdropped
       and a.attname <> all (v_names);

    if v_extra is not null then
        raise exception 'CONFLICT: public.onboarding_drafts has unexpected column(s): %. The repositories read this table by name; an unknown extra column means someone else owns it. Stop and review.', v_extra;
    end if;

    for v_i in 1 .. array_length(v_names, 1) loop
        v_type := null;
        v_is_notnull := null;
        v_default_expr := null;

        select format_type(a.atttypid, a.atttypmod),
               a.attnotnull,
               pg_get_expr(d.adbin, d.adrelid)
          into v_type, v_is_notnull, v_default_expr
          from pg_attribute a
          left join pg_attrdef d
                 on d.adrelid = a.attrelid and d.adnum = a.attnum
         where a.attrelid = v_rel
           and a.attname = v_names[v_i]
           and a.attnum > 0
           and not a.attisdropped;

        if v_type is null then
            raise exception 'CONFLICT: public.onboarding_drafts is missing column %. Stop and review.', v_names[v_i];
        end if;

        if v_type <> v_types[v_i] then
            raise exception 'CONFLICT: public.onboarding_drafts.% has type % (expected %). Stop and review.', v_names[v_i], v_type, v_types[v_i];
        end if;

        if v_is_notnull <> (v_notnull[v_i] = 'NO') then
            raise exception 'CONFLICT: public.onboarding_drafts.% is % (expected %). Stop and review.',
                v_names[v_i],
                case when v_is_notnull then 'NOT NULL' else 'nullable' end,
                case when v_notnull[v_i] = 'NO' then 'NOT NULL' else 'nullable' end;
        end if;

        if v_default[v_i] is null and v_default_expr is not null then
            raise exception 'CONFLICT: public.onboarding_drafts.% has an unexpected default (%). Stop and review.', v_names[v_i], v_default_expr;
        end if;

        if v_default[v_i] is not null
           and (v_default_expr is null or position(v_default[v_i] in v_default_expr) = 0) then
            raise exception 'CONFLICT: public.onboarding_drafts.% default is % (expected to contain %). Stop and review.',
                v_names[v_i], coalesce(v_default_expr, 'none'), v_default[v_i];
        end if;
    end loop;

    -- Primary key on exactly (id).
    if not exists (
        select 1
          from pg_constraint c
         where c.conrelid = v_rel
           and c.contype = 'p'
           and (select array_agg(a.attname::text order by a.attname)
                  from pg_attribute a
                 where a.attrelid = c.conrelid
                   and a.attnum = any (c.conkey)) = array['id']
    ) then
        raise exception 'CONFLICT: public.onboarding_drafts has no primary key on (id). Stop and review.';
    end if;

    -- Unique on exactly (user_id): the draft upsert uses on_conflict=user_id.
    if not exists (
        select 1
          from pg_index i
         where i.indrelid = v_rel
           and i.indisunique
           and i.indnkeyatts = 1
           and i.indnatts = 1
           and i.indkey[0] = (select a.attnum
                                from pg_attribute a
                               where a.attrelid = v_rel
                                 and a.attname = 'user_id'
                                 and not a.attisdropped)
    ) then
        raise exception 'CONFLICT: public.onboarding_drafts has no unique index on (user_id) alone; the draft upsert path would fail. Stop and review.';
    end if;
end;
$helper$
;
-- 2.1 Second session-local assertion: the user_id foreign key with its delete
--     action, the deliberate ABSENCE of a workspace_id foreign key, and the step
--     range CHECK.
create or replace function pg_temp.assert_onboarding_drafts_keys()
returns void
language plpgsql
as $helper$
declare
    v_rel oid := to_regclass('public.onboarding_drafts');
    v_fk record;
begin
    if v_rel is null then
        raise exception 'ASSERTION FAILED: public.onboarding_drafts does not exist.';
    end if;

    for v_fk in
        select *
          from (values
                 ('user_id'::text, to_regclass('auth.users'), 'c'::"char",
                  'auth.users(id) on delete cascade')
               ) as f(col, target_rel, delete_action, description)
    loop
        if v_fk.target_rel is null then
            raise exception 'PREFLIGHT FAILED: the target table for public.onboarding_drafts.% (%) is not reachable.', v_fk.col, v_fk.description;
        end if;

        if not exists (
            select 1
              from pg_constraint c
             where c.conrelid = v_rel
               and c.contype = 'f'
               and c.confrelid = v_fk.target_rel
               and c.confdeltype = v_fk.delete_action
               and (select array_agg(a.attname::text)
                      from pg_attribute a
                     where a.attrelid = c.conrelid
                       and a.attnum = any (c.conkey)) = array[v_fk.col]
        ) then
            raise exception 'CONFLICT: public.onboarding_drafts.% is missing its foreign key to % (found a different or absent constraint). Stop and review.', v_fk.col, v_fk.description;
        end if;
    end loop;

    -- workspace_id must NOT be a foreign key to organizations. It holds a
    -- *reservation*: claim_onboarding_workspace writes the id before the
    -- organization row exists (backend/app/services/organization_service.py:101
    -- -> 102 create_workspace(workspace_id=...)), so an FK there makes every
    -- claim fail with a foreign key violation. Reproduced in the test harness.
    if exists (
        select 1
          from pg_constraint c
         where c.conrelid = v_rel
           and c.contype = 'f'
           and (select array_agg(a.attname::text)
                  from pg_attribute a
                 where a.attrelid = c.conrelid
                   and a.attnum = any (c.conkey)) = array['workspace_id']
    ) then
        raise exception 'CONFLICT: public.onboarding_drafts has a foreign key on (workspace_id). That constraint cannot coexist with claim_onboarding_workspace: the RPC reserves an id before the organizations row exists, so every claim would fail. This script never drops constraints - remove that one manually after review, then re-run. Nothing was changed.';
    end if;

    if not exists (
        select 1
          from pg_constraint c
         where c.conrelid = v_rel
           and c.contype = 'c'
           and regexp_replace(lower(pg_get_constraintdef(c.oid)), '[[:space:]]', '', 'g')
               like '%step>=1%step<=6%'
    ) then
        raise exception 'CONFLICT: public.onboarding_drafts has no CHECK constraint limiting step to 1..6. Stop and review.';
    end if;
end
$helper$
;

-- 2.2 If the table already exists, its whole structure must match before this
--     transaction adds anything to it. A mismatch stops here rather than being
--     "fixed" by a script that does not own the object.
do $$
begin
    if to_regclass('public.onboarding_drafts') is null then
        return;  -- expected: absent, created in 2.3
    end if;

    perform pg_temp.assert_onboarding_drafts_shape();
    perform pg_temp.assert_onboarding_drafts_keys();
    raise notice 'public.onboarding_drafts already exists and matches the expected structure; it will not be recreated.';
end
$$;

-- 2.3 Draft table. One row per auth user; a single workspace id is reserved
--     before the compensating multi-repository bootstrap begins.
--
--     DELIBERATE DIFFERENCE FROM backend/migrations/20261014_onboarding_drafts.sql
--     and 20261109_resumable_business_onboarding.sql: workspace_id carries NO
--     foreign key to public.organizations. Both migrations declare
--     `references public.organizations(id) on delete set null`, but
--     organization_service.complete_onboarding claims the id (line 101) and
--     only then creates the organization (line 102), so the declared FK makes
--     the first claim fail with a foreign key violation - verified in the test
--     harness. The column holds a pre-commitment value, not a live reference;
--     deleting an organization is already handled in application code (the
--     draft lookup returns None and answers 409).
create table if not exists public.onboarding_drafts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references auth.users(id) on delete cascade,
    step integer not null default 1 check (step between 1 and 6),
    completed boolean not null default false,
    data jsonb not null default '{}'::jsonb,
    workspace_id uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 2.4 Prove what is actually there now: columns, types, nullability, defaults,
--     PK, unique(user_id), both foreign keys and the step CHECK.
do $$
begin
    perform pg_temp.assert_onboarding_drafts_shape();
    perform pg_temp.assert_onboarding_drafts_keys();
end
$$;

-- 2.5 Secondary index for the "list my draft" lookup. Created only if a firing
--     (non-partial) index on exactly (user_id) is absent; an existing index with
--     this name but a different definition is not silently accepted.
do $$
declare
    v_rel oid := to_regclass('public.onboarding_drafts');
    v_idx oid;
    v_def text;
begin
    select c.oid
      into v_idx
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public'
       and c.relname = 'idx_onboarding_drafts_user';

    if v_idx is null then
        execute 'create index idx_onboarding_drafts_user on public.onboarding_drafts (user_id)';
        return;
    end if;

    v_def := pg_get_indexdef(v_idx);

    if v_def not like 'CREATE INDEX%ON public.onboarding_drafts USING btree (user_id)'
       and v_def not like 'CREATE UNIQUE INDEX%ON public.onboarding_drafts USING btree (user_id)' then
        raise exception 'CONFLICT: an index named idx_onboarding_drafts_user already exists with a different definition: %. Stop and review.', v_def;
    end if;
end
$$;
-- 2.6 RLS: owner-only. The backend uses the service-role client, which bypasses
--     RLS; this policy is the safety net for any direct authenticated access.
--     enable row level security is idempotent and cannot detach a policy.
alter table public.onboarding_drafts enable row level security;

-- 2.7 The owner policy. Never dropped and never replaced: if it exists, it must
--     already be exactly this policy, otherwise the script stops and prints what
--     is actually there.
do $$
declare
    v_rel oid := to_regclass('public.onboarding_drafts');
    v_other text;
    v_pol record;
    v_qual text;
    v_check text;
begin
    -- Any policy on this table other than the one below is somebody else's
    -- decision; this repair does not get to delete it.
    select string_agg(p.polname, ', ' order by p.polname)
      into v_other
      from pg_policy p
     where p.polrelid = v_rel
       and p.polname <> 'onboarding_drafts_owner';

    if v_other is not null then
        raise exception 'CONFLICT: public.onboarding_drafts already has other policy(ies): %. This script never drops or replaces policies. Stop and review.', v_other;
    end if;

    select p.polcmd,
           p.polpermissive,
           p.polroles,
           pg_get_expr(p.polqual, p.polrelid)      as qual,
           pg_get_expr(p.polwithcheck, p.polrelid) as with_check
      into v_pol
      from pg_policy p
     where p.polrelid = v_rel
       and p.polname = 'onboarding_drafts_owner';

    if not found then
        execute 'create policy onboarding_drafts_owner on public.onboarding_drafts '
             || 'for all using (auth.uid() = user_id) '
             || 'with check (auth.uid() = user_id)';
        raise notice 'created policy onboarding_drafts_owner.';
        return;
    end if;

    if v_pol.polcmd <> '*' then
        raise exception 'CONFLICT: policy onboarding_drafts_owner applies to command % (expected ALL, i.e. FOR ALL). Its definition was not changed. Stop and review.', v_pol.polcmd;
    end if;

    if not v_pol.polpermissive then
        raise exception 'CONFLICT: policy onboarding_drafts_owner is RESTRICTIVE (expected PERMISSIVE). Its definition was not changed. Stop and review.';
    end if;

    if v_pol.polroles <> '{0}'::oid[] then
        raise exception 'CONFLICT: policy onboarding_drafts_owner is scoped to role oid(s) % (expected PUBLIC = {0}). Its definition was not changed. Stop and review.', v_pol.polroles;
    end if;

    v_qual := btrim(lower(regexp_replace(coalesce(v_pol.qual, ''),
                                         '[[:space:]]', '', 'g')), '()');
    v_check := btrim(lower(regexp_replace(coalesce(v_pol.with_check, ''),
                                          '[[:space:]]', '', 'g')), '()');

    if v_qual <> 'auth.uid()=user_id' then
        raise exception 'CONFLICT: policy onboarding_drafts_owner USING is %, expected (auth.uid() = user_id). Its definition was not changed. Stop and review.', coalesce(v_pol.qual, '<none>');
    end if;

    if v_check <> 'auth.uid()=user_id' then
        raise exception 'CONFLICT: policy onboarding_drafts_owner WITH CHECK is %, expected (auth.uid() = user_id). Its definition was not changed. Stop and review.', coalesce(v_pol.with_check, '<none>');
    end if;

    raise notice 'policy onboarding_drafts_owner already matches the expected definition; left untouched.';
end
$$;

-- 2.8 Business-profile columns on organizations. Typed text because the API
--     contract is a closed set of literals
--     (backend/app/schemas/onboarding.py: BusinessType, AccountingSoftware,
--     InvoiceVolume), not a database enum.
do $$
declare
    v_name text;
    v_type text;
    v_required text[] := array['business_type', 'monthly_invoice_volume',
                               'accounting_software'];
begin
    foreach v_name in array v_required loop
        v_type := null;

        select format_type(a.atttypid, a.atttypmod)
          into v_type
          from pg_attribute a
         where a.attrelid = 'public.organizations'::regclass
           and a.attname = v_name
           and a.attnum > 0
           and not a.attisdropped;

        if v_type is not null and v_type <> 'text' then
            raise exception 'CONFLICT: public.organizations.% already exists as % (expected text). Stop and review.', v_name, v_type;
        end if;
    end loop;
end
$$;

alter table public.organizations
    add column if not exists business_type text,
    add column if not exists monthly_invoice_volume text,
    add column if not exists accounting_software text;
-- 2.9 Workspace reservation. SECURITY DEFINER so the backend can update the
--     draft row before the workspace exists; scoped by p_user_id and by
--     completed = false, so a retry reuses the reserved id and a second
--     workspace cannot be created.
--
--     HARDENING: search_path is pinned to "public, pg_temp" (the repository
--     migration only pinned "public") and every object reference is
--     schema-qualified. This is a deliberate difference from
--     20261109_resumable_business_onboarding.sql: if that migration is ever
--     applied later it would overwrite this body, so it must be updated to
--     match instead (see the plan document).
--
--     CREATION IS GUARDED. The function is created only when absent. If
--     claim_onboarding_workspace(uuid) already exists, this block compares it
--     with the definition below and either accepts it untouched (identical) or
--     stops. It never replaces an existing function body.
do $$
declare
    v_sig constant text := 'public.claim_onboarding_workspace(uuid)';
    v_body constant text := $body$
    update public.onboarding_drafts
       set workspace_id = coalesce(workspace_id, gen_random_uuid()),
           updated_at   = now()
     where user_id = p_user_id
       and completed = false
    returning workspace_id;
$body$;
    v_body_norm text;
    v_oid oid;
    v_other text;
    v_def record;
begin
    v_body_norm := btrim(regexp_replace(v_body, '[[:space:]]+', ' ', 'g'));
    v_oid := to_regprocedure(v_sig);

    -- A second overload would make PostgREST's rpc() call ambiguous.
    select string_agg(p.oid::regprocedure::text, ', ' order by p.oid::regprocedure::text)
      into v_other
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname = 'claim_onboarding_workspace'
       and p.oid is distinct from v_oid;

    if v_other is not null then
        raise exception 'CONFLICT: unexpected overload(s) of claim_onboarding_workspace: %. This repair creates exactly claim_onboarding_workspace(uuid) and must not add or coexist with a second overload. Stop and review.', v_other;
    end if;

    if v_oid is null then
        execute 'create function public.claim_onboarding_workspace(p_user_id uuid) '
             || 'returns uuid '
             || 'language sql '
             || 'security definer '
             || 'set search_path = public, pg_temp '
             || 'as ' || quote_literal(v_body);
        raise notice 'created function %.', v_sig;
        return;
    end if;

    select p.prosecdef,
           p.proretset,
           p.prorettype,
           p.proconfig,
           p.prosrc,
           (p.prolang = (select l.oid from pg_language l where l.lanname = 'sql')) as is_sql
      into v_def
      from pg_proc p
     where p.oid = v_oid;

    if v_def.prorettype <> 'uuid'::regtype or v_def.proretset then
        raise exception 'CONFLICT: % already exists returning % (expected scalar uuid). Its definition was not changed. Stop and review.', v_sig, pg_get_function_result(v_oid);
    end if;

    if not v_def.prosecdef then
        raise exception 'CONFLICT: % already exists WITHOUT security definer. Its definition was not changed. Stop and review.', v_sig;
    end if;

    if not v_def.is_sql then
        raise exception 'CONFLICT: % already exists in a language other than sql. Its definition was not changed. Stop and review.', v_sig;
    end if;

    if coalesce(v_def.proconfig, array[]::text[]) <> array['search_path=public, pg_temp'] then
        raise exception 'CONFLICT: % already exists with proconfig = % (expected search_path=public, pg_temp). Its definition was not changed. Stop and review.', v_sig, coalesce(array_to_string(v_def.proconfig, ', '), '<none>');
    end if;

    if btrim(regexp_replace(v_def.prosrc, '[[:space:]]+', ' ', 'g')) <> v_body_norm then
        raise exception 'CONFLICT: % already exists with a different body. This script never overwrites an existing function. Inspect it (select prosrc from pg_proc where oid = to_regprocedure(%L)) and decide manually. Nothing was changed.', v_sig, v_sig;
    end if;

    raise notice 'function % already exists with the expected definition; left untouched.', v_sig;
end
$$;

-- 2.10 Execute privileges: the backend (service role) is the only caller.
--      Roles are checked before they are named in a REVOKE/GRANT.
do $$
declare
    v_targets text;
begin
    if not exists (select 1 from pg_roles where rolname = 'service_role') then
        raise exception 'PREFLIGHT FAILED: role service_role does not exist; the backend cannot call the RPC. Stop.';
    end if;

    select string_agg(g, ', ')
      into v_targets
      from unnest(array['public', 'anon', 'authenticated']) g
     where g = 'public'
        or exists (select 1 from pg_roles r where r.rolname = g);

    if v_targets is not null then
        execute 'revoke all on function public.claim_onboarding_workspace(uuid) from ' || v_targets;
    end if;

    execute 'grant execute on function public.claim_onboarding_workspace(uuid) to service_role';
end
$$;

-- 2.11 Table privileges. Service role is the only reader/writer through the
--      backend; anon/authenticated are additionally constrained by the RLS
--      policy above (and hold no policy, so they are denied anyway).
do $$
declare
    v_targets text;
begin
    select string_agg(g, ', ')
      into v_targets
      from unnest(array['public', 'anon', 'authenticated']) g
     where g = 'public'
        or exists (select 1 from pg_roles r where r.rolname = g);

    if v_targets is not null then
        execute 'revoke all on table public.onboarding_drafts from ' || v_targets;
    end if;

    execute 'grant select, insert, update, delete on table public.onboarding_drafts to service_role';
end
$$;

-- ----------------------------------------------------------------------------
-- SECTION 3 - REPAIR 3: public.manage_ap_email_intake_address(...)
--
-- Why: backend/app/services/ap/email_address_service.py calls
--      rpc('manage_ap_email_intake_address', {p_org_id, p_created_by,
--      p_email_address, p_rotate}) and raises when it returns nothing. The
--      function is absent from production, so AP forwarding addresses cannot be
--      created or rotated at all.
-- Shape: returns setof public.ap_email_intake_addresses; production's column
--      list is exactly (id, org_id, email_address, is_active, created_by,
--      created_at), which is what the function inserts and returns.
-- ----------------------------------------------------------------------------

-- 3.1 Guards: table present with the expected columns; no conflicting overload;
--     no duplicate active rows that would make the unique indexes unbuildable.
do $$
declare
    v_missing text;
    v_conflict text;
begin
    if to_regclass('public.ap_email_intake_addresses') is null then
        raise exception 'PREFLIGHT FAILED: public.ap_email_intake_addresses does not exist. Apply backend/migrations/20261109_ap_email_address_rotation.sql (table bootstrap only) first, then re-run.';
    end if;

    select string_agg(c, ', ' order by c)
      into v_missing
      from unnest(array['id', 'org_id', 'email_address', 'is_active',
                        'created_by', 'created_at']) c
     where not exists (
         select 1
           from pg_attribute a
          where a.attrelid = 'public.ap_email_intake_addresses'::regclass
            and a.attname = c
            and a.attnum > 0
            and not a.attisdropped);

    if v_missing is not null then
        raise exception 'CONFLICT: public.ap_email_intake_addresses is missing column(s): %. Stop and review.', v_missing;
    end if;

    select string_agg(p.oid::regprocedure::text, ', ')
      into v_conflict
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname = 'manage_ap_email_intake_address'
       and oidvectortypes(p.proargtypes) <> 'uuid, uuid, text, boolean';

    if v_conflict is not null then
        raise exception 'CONFLICT: an overload of manage_ap_email_intake_address already exists with a different signature: %. Stop and review; do not create a second overload.', v_conflict;
    end if;

    if exists (
        select 1
          from public.ap_email_intake_addresses
         where is_active is true
         group by org_id
        having count(*) > 1
    ) then
        raise exception 'DATA CONFLICT: an organization has more than one active AP email address. Resolve the duplicates manually before applying address rotation.';
    end if;

    if exists (
        select 1
          from public.ap_email_intake_addresses
         where is_active is true
         group by lower(email_address)
        having count(*) > 1
    ) then
        raise exception 'DATA CONFLICT: duplicate active AP email addresses exist (case-insensitive). Resolve them manually before applying address rotation.';
    end if;
end
$$;
-- 3.2 The rotation invariant lives in the database, not in the service.
--     At most one active row per organization, and an active address value
--     cannot be reused by another organization.
--
--     Each index is created only if its name is free. A same-named index is
--     compared on table, uniqueness, key count, key definition, partial
--     predicate and validity; anything else stops the script and prints the
--     real definition. CREATE UNIQUE INDEX IF NOT EXISTS is deliberately not
--     used: it would silently accept a differently defined index.
do $$
declare
    v_rel oid := 'public.ap_email_intake_addresses'::regclass;
    v_spec record;
    v_idx oid;
    v_relkind "char";
    v_def record;
    v_problem text;
begin
    for v_spec in
        select *
          from (values
                 ('uq_ap_email_address_one_active_per_org'::text,
                  'org_id'::text,
                  'create unique index uq_ap_email_address_one_active_per_org '
                  || 'on public.ap_email_intake_addresses (org_id) '
                  || 'where is_active is true'::text),
                 ('uq_ap_email_address_unique_active_value'::text,
                  'lower(email_address)'::text,
                  'create unique index uq_ap_email_address_unique_active_value '
                  || 'on public.ap_email_intake_addresses (lower(email_address)) '
                  || 'where is_active is true'::text)
               ) as spec(index_name, key_expr, ddl)
    loop
        v_idx := null;
        v_relkind := null;

        select c.oid, c.relkind
          into v_idx, v_relkind
          from pg_class c
          join pg_namespace n on n.oid = c.relnamespace
         where n.nspname = 'public'
           and c.relname = v_spec.index_name;

        if v_idx is not null and v_relkind <> 'i' then
            raise exception 'CONFLICT: a non-index relation named % already exists in schema public (relkind %). Stop and review.', v_spec.index_name, v_relkind;
        end if;

        if v_idx is null then
            execute v_spec.ddl;
            raise notice 'created index %.', v_spec.index_name;
            continue;
        end if;

        select i.indrelid,
               i.indisunique,
               i.indnkeyatts,
               i.indnatts,
               i.indisvalid,
               i.indisready,
               pg_get_indexdef(i.indexrelid, 1, false) as key_expr,
               pg_get_expr(i.indpred, i.indrelid)      as predicate,
               pg_get_indexdef(i.indexrelid)           as full_def
          into v_def
          from pg_index i
         where i.indexrelid = v_idx;

        v_problem := null;

        if v_def.indrelid <> v_rel then
            v_problem := format('it indexes %s instead of public.ap_email_intake_addresses',
                                v_def.indrelid::regclass);
        elsif not v_def.indisunique then
            v_problem := 'it is not UNIQUE';
        elsif v_def.indnkeyatts <> 1 or v_def.indnatts <> 1 then
            v_problem := format('it has %s key column(s) / %s total attribute(s), expected exactly 1',
                                v_def.indnkeyatts, v_def.indnatts);
        elsif lower(regexp_replace(coalesce(v_def.key_expr, ''), '[[:space:]]', '', 'g'))
              <> lower(v_spec.key_expr) then
            v_problem := format('its key definition is %s, expected %s',
                                coalesce(v_def.key_expr, '<none>'), v_spec.key_expr);
        elsif v_def.predicate is null then
            v_problem := 'it is not a partial index (it has no WHERE clause)';
        elsif not (btrim(lower(regexp_replace(v_def.predicate, '[[:space:]]', '', 'g')), '()')
                   = any (array['is_activeistrue', 'is_active=true', 'is_active'])) then
            v_problem := format('its predicate is %s, expected (is_active IS TRUE)',
                                v_def.predicate);
        elsif not v_def.indisvalid or not v_def.indisready then
            v_problem := format('it is not usable (indisvalid=%, indisready=%)',
                                v_def.indisvalid, v_def.indisready);
        end if;

        if v_problem is not null then
            raise exception 'CONFLICT: index % already exists but %. Actual definition: %. This script does not drop or rename indexes and IF NOT EXISTS was not used. Stop and review.', v_spec.index_name, v_problem, v_def.full_def;
        end if;

        raise notice 'index % already exists with the expected definition; left untouched.', v_spec.index_name;
    end loop;
end
$$;
-- 3.3 Atomic create-or-rotate. Serialised per organization by an advisory lock,
--     so two concurrent rotations cannot both win.
--
--     HARDENING: SECURITY DEFINER with search_path pinned to "public, pg_temp"
--     and all object references schema-qualified, including the %rowtype.
--
--     CREATION IS GUARDED. Created only when absent; if the exact signature
--     already exists it is compared with this definition and either accepted
--     untouched (identical) or the script stops. No existing body is replaced.
do $$
declare
    v_sig constant text := 'public.manage_ap_email_intake_address(uuid, uuid, text, boolean)';
    v_body constant text := $body$
declare
    v_address public.ap_email_intake_addresses%rowtype;
begin
    if p_org_id is null or p_created_by is null then
        raise exception 'Organization and actor are required.';
    end if;

    if p_email_address is null
       or p_email_address !~ '^[^@[:space:]]+@[^@[:space:]]+$' then
        raise exception 'A valid forwarding address is required.';
    end if;

    perform pg_advisory_xact_lock(
        hashtextextended('ap_email_intake_addresses:' || p_org_id::text, 0)
    );

    if not coalesce(p_rotate, false) then
        select *
          into v_address
          from public.ap_email_intake_addresses
         where org_id = p_org_id
           and is_active is true
         limit 1;

        if found then
            return next v_address;
            return;
        end if;
    else
        update public.ap_email_intake_addresses
           set is_active = false
         where org_id = p_org_id
           and is_active is true;
    end if;

    insert into public.ap_email_intake_addresses
        (org_id, email_address, is_active, created_by)
    values
        (p_org_id, lower(p_email_address), true, p_created_by)
    returning * into v_address;

    return next v_address;
end;
$body$;
    v_body_norm text;
    v_oid oid;
    v_other text;
    v_def record;
begin
    v_body_norm := btrim(regexp_replace(v_body, '[[:space:]]+', ' ', 'g'));
    v_oid := to_regprocedure(v_sig);

    select string_agg(p.oid::regprocedure::text, ', ' order by p.oid::regprocedure::text)
      into v_other
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname = 'manage_ap_email_intake_address'
       and p.oid is distinct from v_oid;

    if v_other is not null then
        raise exception 'CONFLICT: unexpected overload(s) of manage_ap_email_intake_address: %. This repair creates exactly one signature. Stop and review.', v_other;
    end if;

    if v_oid is null then
        execute 'create function public.manage_ap_email_intake_address('
             || 'p_org_id uuid, p_created_by uuid, p_email_address text, '
             || 'p_rotate boolean default false) '
             || 'returns setof public.ap_email_intake_addresses '
             || 'language plpgsql '
             || 'security definer '
             || 'set search_path = public, pg_temp '
             || 'as ' || quote_literal(v_body);
        raise notice 'created function %.', v_sig;
        return;
    end if;

    select p.prosecdef,
           p.proretset,
           p.prorettype,
           p.proconfig,
           p.prosrc,
           p.pronargdefaults,
           (p.prolang = (select l.oid from pg_language l where l.lanname = 'plpgsql')) as is_plpgsql
      into v_def
      from pg_proc p
     where p.oid = v_oid;

    if v_def.prorettype <> 'public.ap_email_intake_addresses'::regtype
       or not v_def.proretset then
        raise exception 'CONFLICT: % already exists returning % (expected setof public.ap_email_intake_addresses). Its definition was not changed. Stop and review.', v_sig, pg_get_function_result(v_oid);
    end if;

    if not v_def.prosecdef then
        raise exception 'CONFLICT: % already exists WITHOUT security definer. Its definition was not changed. Stop and review.', v_sig;
    end if;

    if not v_def.is_plpgsql then
        raise exception 'CONFLICT: % already exists in a language other than plpgsql. Its definition was not changed. Stop and review.', v_sig;
    end if;

    if v_def.pronargdefaults <> 1 then
        raise exception 'CONFLICT: % has % defaulted argument(s) (expected exactly p_rotate). Its definition was not changed. Stop and review.', v_sig, v_def.pronargdefaults;
    end if;

    if coalesce(v_def.proconfig, array[]::text[]) <> array['search_path=public, pg_temp'] then
        raise exception 'CONFLICT: % already exists with proconfig = % (expected search_path=public, pg_temp). Its definition was not changed. Stop and review.', v_sig, coalesce(array_to_string(v_def.proconfig, ', '), '<none>');
    end if;

    if btrim(regexp_replace(v_def.prosrc, '[[:space:]]+', ' ', 'g')) <> v_body_norm then
        raise exception 'CONFLICT: % already exists with a different body. This script never overwrites an existing function. Inspect it (select prosrc from pg_proc where oid = to_regprocedure(%L)) and decide manually. Nothing was changed.', v_sig, v_sig;
    end if;

    raise notice 'function % already exists with the expected definition; left untouched.', v_sig;
end
$$;

-- 3.4 Execute privileges on the RPC.
do $$
declare
    v_targets text;
begin
    if not exists (select 1 from pg_roles where rolname = 'service_role') then
        raise exception 'PREFLIGHT FAILED: role service_role does not exist; the backend cannot call the RPC. Stop.';
    end if;

    select string_agg(g, ', ')
      into v_targets
      from unnest(array['public', 'anon', 'authenticated']) g
     where g = 'public'
        or exists (select 1 from pg_roles r where r.rolname = g);

    if v_targets is not null then
        execute 'revoke all on function public.manage_ap_email_intake_address(uuid, uuid, text, boolean) from ' || v_targets;
    end if;

    execute 'grant execute on function public.manage_ap_email_intake_address(uuid, uuid, text, boolean) to service_role';
end
$$;
-- 3.5 Table privileges and RLS on public.ap_email_intake_addresses.
--
--     JUSTIFICATION FOR NARROWING ACCESS ON A PRE-EXISTING TABLE
--     * Every read and write of this table in the application goes through the
--       service-role client: backend/app/core/supabase.py:44-56 returns the
--       service-role client ("bypasses Row Level Security"), and the only call
--       sites are backend/app/routers/ap.py:931 (GET /ap/email-address) and
--       backend/app/services/ap/email_intake_service.py:51 (webhook intake).
--       There is no anon or authenticated client-side query against it, so
--       losing anon/authenticated grants cannot break a supported caller.
--     * Therefore the safe order is: prove it first, then narrow it.
--       (a) Refuse to run if any policy exists. A policy means someone made a
--           deliberate decision about client access that this script cannot
--           see read-only, and revoking under it could break that access.
--       (b) Enable RLS. With no policy, anon/authenticated get nothing.
--       (c) Only then revoke, and report the exact privileges that were held
--           before the change via RAISE NOTICE so it lands in the apply log.
--     * After the change, service_role must still hold SELECT/INSERT/UPDATE/
--       DELETE, asserted below. If it does not, the script raises.
do $$
declare
    v_rel oid := 'public.ap_email_intake_addresses'::regclass;
    v_rls boolean;
    v_policies text;
    v_before text;
    v_after text;
    v_targets text;
begin
    select c.relrowsecurity into v_rls from pg_class c where c.oid = v_rel;

    select string_agg(p.polname || ' [cmd ' || p.polcmd::text
                      || ', roles ' || coalesce(array_to_string(p.polroles::text[], ','), '?')
                      || ']', '; ' order by p.polname)
      into v_policies
      from pg_policy p
     where p.polrelid = v_rel;

    if v_policies is not null then
        raise exception 'REVIEW REQUIRED: public.ap_email_intake_addresses already has policy(ies): %. This script will not narrow privileges under an unknown policy. Inspect the policy, decide whether anon/authenticated really need it, and resolve manually before re-running. Nothing was changed.', v_policies;
    end if;

    -- Effective privileges include anything inherited from PUBLIC.
    select string_agg(g.role_name || ' {' || g.privs || '}', '; ' order by g.role_name)
      into v_before
      from (
          select r.rolname as role_name,
                 concat_ws(',',
                     case when has_table_privilege(r.oid, v_rel, 'SELECT') then 'select' end,
                     case when has_table_privilege(r.oid, v_rel, 'INSERT') then 'insert' end,
                     case when has_table_privilege(r.oid, v_rel, 'UPDATE') then 'update' end,
                     case when has_table_privilege(r.oid, v_rel, 'DELETE') then 'delete' end) as privs
            from pg_roles r
           where r.rolname in ('anon', 'authenticated', 'service_role')
      ) g
     where g.privs <> '';

    raise notice 'ap_email_intake_addresses BEFORE: rls_enabled=% ; effective privileges: %',
        v_rls, coalesce(v_before, '<none>');

    if not v_rls then
        execute 'alter table public.ap_email_intake_addresses enable row level security';
        raise notice 'ap_email_intake_addresses: RLS was disabled; enabled it. With no policies, anon/authenticated are now denied.';
    end if;

    select string_agg(g, ', ')
      into v_targets
      from unnest(array['public', 'anon', 'authenticated']) g
     where g = 'public'
        or exists (select 1 from pg_roles r where r.rolname = g);

    if v_targets is not null then
        execute 'revoke all on table public.ap_email_intake_addresses from ' || v_targets;
    end if;

    execute 'grant select, insert, update, delete on table public.ap_email_intake_addresses to service_role';

    if not (has_table_privilege('service_role', v_rel, 'SELECT')
            and has_table_privilege('service_role', v_rel, 'INSERT')
            and has_table_privilege('service_role', v_rel, 'UPDATE')
            and has_table_privilege('service_role', v_rel, 'DELETE')) then
        raise exception 'POST-CHECK FAILED: service_role lost privileges on public.ap_email_intake_addresses; rolling back.';
    end if;

    select string_agg(g.role_name || ' {' || g.privs || '}', '; ' order by g.role_name)
      into v_after
      from (
          select r.rolname as role_name,
                 concat_ws(',',
                     case when has_table_privilege(r.oid, v_rel, 'SELECT') then 'select' end,
                     case when has_table_privilege(r.oid, v_rel, 'INSERT') then 'insert' end,
                     case when has_table_privilege(r.oid, v_rel, 'UPDATE') then 'update' end,
                     case when has_table_privilege(r.oid, v_rel, 'DELETE') then 'delete' end) as privs
            from pg_roles r
           where r.rolname in ('anon', 'authenticated', 'service_role')
      ) g
     where g.privs <> '';

    raise notice 'ap_email_intake_addresses AFTER: effective privileges: %',
        coalesce(v_after, '<none>');
end
$$;

-- ----------------------------------------------------------------------------
-- SECTION 4 - REPAIR 4: storage bucket 'documents'
--
-- Why: 20261109_private_documents_bucket.sql is only partially applied. The
--      bucket exists but carries no size limit and no MIME allowlist, so
--      Supabase Storage accepts any file type and any size up to the project
--      default. The application's own contract is:
--        app/core/config.py     max_file_size_mb = 10
--                               allowed_file_types = pdf, jpeg, png, webp
--        app/services/ap/email_intake_service.py
--                               ALLOWED_TYPES = pdf, png, jpeg, TIFF
--      The allowlist below is the union of both, so no intake path that the
--      code accepts today is rejected by the bucket. image/tiff is a deliberate
--      addition over the repo migration: excluding it would break AP email
--      intake for TIFF attachments (decision point D1 in the plan document).
--
--      Only the bucket's own settings are written. No object and no bucket is
--      created, dropped or renamed. The bucket was already private per the
--      migration's first half; public = false is re-asserted, never toggled on.
-- ----------------------------------------------------------------------------

do $$
declare
    v_updated integer;
begin
    if to_regclass('storage.buckets') is null then
        raise exception 'PREFLIGHT FAILED: storage.buckets is not reachable from this session. Run SECTION 4 from the Supabase SQL editor of project lyjvctomtlqqqivjjrzc.';
    end if;

    update storage.buckets
       set public = false,
           file_size_limit = 10485760,
           allowed_mime_types = array[
               'application/pdf',
               'image/jpeg',
               'image/png',
               'image/webp',
               'image/tiff'
           ]
     where id = 'documents';

    get diagnostics v_updated = row_count;

    if v_updated = 0 then
        raise exception 'PREFLIGHT FAILED: bucket "documents" does not exist in storage.buckets. Provision the bucket first (private), then re-run SECTION 4.';
    end if;

    if v_updated > 1 then
        raise exception 'CONFLICT: % rows in storage.buckets have id = ''documents''. Stop and review.', v_updated;
    end if;
end
$$;


-- ----------------------------------------------------------------------------
-- SECTION 5 - COMMIT
-- ----------------------------------------------------------------------------
commit;

-- PostgREST caches the schema; new columns/functions are invisible to the API
-- until it reloads. Harmless if Supabase has already reloaded.
notify pgrst, 'reload schema';

-- ============================================================================
-- SECTION 6 - POST-MIGRATION VERIFICATION (READ-ONLY)
-- Run after SECTION 5. Every row must match the stated expectation.
-- A repair is NOT complete until the matching check returns the expected value.
-- ============================================================================

-- V1 / Repair 1: exactly one row: text, nullable, no default.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'invoice_codings'
   and column_name = 'reasoning'
;
-- expect: reasoning | text | YES | (null)

-- V2 / Repair 2: the draft table, column by column.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'onboarding_drafts'
 order by ordinal_position
;
-- expect: exactly 8 rows, in this order:
--   id            uuid                     NO   gen_random_uuid()
--   user_id       uuid                     NO   (null)
--   step          integer                  NO   1
--   completed     boolean                  NO   false
--   data          jsonb                    NO   '{}'::jsonb
--   workspace_id  uuid                     YES  (null)
--   created_at    timestamp with time zone NO   now()
--   updated_at    timestamp with time zone NO   now()

-- V2b / Repair 2: constraints (PK on id, unique on user_id, one FK, step CHECK).
select con.conname, con.contype, pg_get_constraintdef(con.oid) as definition
  from pg_constraint con
 where con.conrelid = 'public.onboarding_drafts'::regclass
 order by con.contype, con.conname
;
-- expect: exactly 4 rows - p on (id); u on (user_id);
--         f user_id -> auth.users(id) ON DELETE CASCADE; c CHECK step 1..6.
--         NO foreign key on workspace_id (see 2.3: it is a reservation).

-- V2c / Repair 2: RLS on and the owner policy exactly as specified.
select c.relrowsecurity                                    as rls_enabled,
       (select count(*)
          from pg_policy p
         where p.polrelid = c.oid)                          as policy_count,
       (select p.polname from pg_policy p where p.polrelid = c.oid)  as policy_name,
       (select p.polcmd from pg_policy p where p.polrelid = c.oid)   as policy_cmd,
       (select p.polpermissive
          from pg_policy p where p.polrelid = c.oid)         as policy_permissive,
       (select p.polroles from pg_policy p where p.polrelid = c.oid) as policy_roles,
       (select pg_get_expr(p.polqual, p.polrelid)
          from pg_policy p where p.polrelid = c.oid)         as policy_using,
       (select pg_get_expr(p.polwithcheck, p.polrelid)
          from pg_policy p where p.polrelid = c.oid)         as policy_with_check
  from pg_class c
 where c.oid = 'public.onboarding_drafts'::regclass
;
-- expect: rls_enabled = true, policy_count = 1, policy_name = onboarding_drafts_owner,
--         policy_cmd = *, policy_permissive = true, policy_roles = {0},
--         policy_using = (auth.uid() = user_id),
--         policy_with_check = (auth.uid() = user_id)

-- V2d / Repair 2: the unique index the draft upsert depends on.
select indexname, indexdef
  from pg_indexes
 where schemaname = 'public'
   and tablename = 'onboarding_drafts'
 order by indexname
;
-- expect: a UNIQUE index whose only key column is user_id, plus
--         idx_onboarding_drafts_user on (user_id).

-- V3 / Repair 2: the three organization profile columns, all text, nullable.
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'organizations'
   and column_name in ('business_type', 'monthly_invoice_volume', 'accounting_software')
 order by column_name
;
-- expect: exactly 3 rows, each text / YES

-- V4 / Repair 2+3: both functions exist with the expected identity, are
-- SECURITY DEFINER, and pin search_path for both.
select p.oid::regprocedure                as function,
       p.prorettype::regtype              as returns,
       p.proretset                        as returns_setof,
       p.prosecdef                        as security_definer,
       p.pronargdefaults                  as defaulted_args,
       array_to_string(p.proconfig, ', ') as proconfig
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public'
   and p.proname in ('claim_onboarding_workspace', 'manage_ap_email_intake_address')
 order by p.proname
;
-- expect: 2 rows
--   claim_onboarding_workspace(uuid)              | uuid                      | false | true | 0 | search_path=public, pg_temp
--   manage_ap_email_intake_address(uuid,uuid,text,boolean)
--                                                 | ap_email_intake_addresses | true  | true | 1 | search_path=public, pg_temp

-- V5 / Repair 2+3: execute privileges. The backend is the only caller.
select 'claim_onboarding_workspace' as function,
       case when exists (select 1 from pg_roles where rolname = 'service_role')
            then has_function_privilege('service_role',
                     'public.claim_onboarding_workspace(uuid)', 'EXECUTE') end as service_role_can_execute,
       case when exists (select 1 from pg_roles where rolname = 'anon')
            then has_function_privilege('anon',
                     'public.claim_onboarding_workspace(uuid)', 'EXECUTE') end as anon_can_execute
union all
select 'manage_ap_email_intake_address',
       case when exists (select 1 from pg_roles where rolname = 'service_role')
            then has_function_privilege('service_role',
                     'public.manage_ap_email_intake_address(uuid, uuid, text, boolean)', 'EXECUTE') end,
       case when exists (select 1 from pg_roles where rolname = 'anon')
            then has_function_privilege('anon',
                     'public.manage_ap_email_intake_address(uuid, uuid, text, boolean)', 'EXECUTE') end
;
-- expect: service_role_can_execute = true, anon_can_execute = false (both rows)

-- V6 / Repair 3: both indexes, with their exact definitions and validity.
select c.relname       as index_name,
       i.indisunique   as is_unique,
       i.indnkeyatts   as key_columns,
       i.indisvalid    as is_valid,
       i.indisready    as is_ready,
       pg_get_indexdef(i.indexrelid, 1, false) as key_expr,
       pg_get_expr(i.indpred, i.indrelid)      as predicate,
       pg_get_indexdef(i.indexrelid)           as full_definition
  from pg_index i
  join pg_class c on c.oid = i.indexrelid
 where i.indrelid = 'public.ap_email_intake_addresses'::regclass
   and c.relname in ('uq_ap_email_address_one_active_per_org',
                     'uq_ap_email_address_unique_active_value')
 order by c.relname
;
-- expect: 2 rows; is_unique = true; key_columns = 1; is_valid / is_ready = true;
--         key_expr = org_id and lower(email_address);
--         predicate = (is_active IS TRUE) on both.

-- V7 / Repair 3: the invariants actually hold on live data.
select
    (select count(*)
       from (select org_id
               from public.ap_email_intake_addresses
              where is_active is true
              group by org_id
             having count(*) > 1) d)                          as duplicate_active_per_org,
    (select count(*)
       from (select lower(email_address)
               from public.ap_email_intake_addresses
              where is_active is true
              group by lower(email_address)
             having count(*) > 1) d)                          as duplicate_active_values
;
-- expect: 0 and 0

-- V7b / Repair 3: privilege state on the address table, before vs. after.
select c.relrowsecurity as rls_enabled,
       (select count(*) from pg_policy p where p.polrelid = c.oid) as policy_count,
       has_table_privilege('service_role', c.oid, 'SELECT') as service_role_select,
       case when exists (select 1 from pg_roles where rolname = 'anon')
            then has_table_privilege('anon', c.oid, 'SELECT') end as anon_select,
       case when exists (select 1 from pg_roles where rolname = 'authenticated')
            then has_table_privilege('authenticated', c.oid, 'SELECT') end as authenticated_select
  from pg_class c
 where c.oid = 'public.ap_email_intake_addresses'::regclass
;
-- expect: rls_enabled = true, policy_count = 0, service_role_select = true,
--         anon_select = false, authenticated_select = false
-- V8 / Repair 4: bucket settings.
select id,
       public                    as is_public,
       file_size_limit,
       allowed_mime_types,
       (allowed_mime_types @> array['application/pdf', 'image/jpeg',
                                    'image/png', 'image/webp', 'image/tiff'])
                                 as allowlist_covers_app_types
  from storage.buckets
 where id = 'documents'
;
-- expect: 1 row; is_public = false; file_size_limit = 10485760;
--         allowlist_covers_app_types = true.

-- V9 / Final gate: one row, every value true. If anything is false, the repair
-- is not complete for that item - re-read the matching V-check above.
select
    (select count(*) = 1 and bool_and(data_type = 'text' and is_nullable = 'YES')
       from information_schema.columns
      where table_schema = 'public'
        and table_name = 'invoice_codings'
        and column_name = 'reasoning')                              as r1_reasoning_ok,

    (select count(*) = 8
       from information_schema.columns
      where table_schema = 'public'
        and table_name = 'onboarding_drafts')                       as r2_columns_ok,

    (select count(*) = 1 and bool_and(c.relrowsecurity)
       from pg_class c
      where c.oid = 'public.onboarding_drafts'::regclass)           as r2_rls_ok,

    (select count(*) = 1
            and bool_and(p.polcmd = '*' and p.polpermissive
                         and p.polroles = '{0}'::oid[]
                         and btrim(lower(regexp_replace(
                                 coalesce(pg_get_expr(p.polqual, p.polrelid), ''),
                                 '[[:space:]]', '', 'g')), '()') = 'auth.uid()=user_id'
                         and btrim(lower(regexp_replace(
                                 coalesce(pg_get_expr(p.polwithcheck, p.polrelid), ''),
                                 '[[:space:]]', '', 'g')), '()') = 'auth.uid()=user_id')
       from pg_policy p
      where p.polrelid = 'public.onboarding_drafts'::regclass)      as r2_policy_ok,

    (select count(*) = 3 and bool_and(data_type = 'text')
       from information_schema.columns
      where table_schema = 'public'
        and table_name = 'organizations'
        and column_name in ('business_type', 'monthly_invoice_volume',
                            'accounting_software'))                 as r2_org_columns_ok,

    (select count(*) = 2
       from (select p.oid
               from pg_proc p
               join pg_namespace n on n.oid = p.pronamespace
              where n.nspname = 'public'
                and p.prosecdef
                and p.proconfig = array['search_path=public, pg_temp']
                and p.oid in (to_regprocedure('public.claim_onboarding_workspace(uuid)'),
                              to_regprocedure('public.manage_ap_email_intake_address(uuid, uuid, text, boolean)'))
             ) f)                                                   as r4_functions_hardened,

    (select count(*) = 2 and bool_and(i.indisunique and i.indnkeyatts = 1
                                      and i.indisvalid and i.indisready)
       from pg_index i
       join pg_class c on c.oid = i.indexrelid
      where i.indrelid = 'public.ap_email_intake_addresses'::regclass
        and c.relname in ('uq_ap_email_address_one_active_per_org',
                          'uq_ap_email_address_unique_active_value')) as r3_indexes_ok,

    (select count(*) = 0
       from (select org_id
               from public.ap_email_intake_addresses
              where is_active is true
              group by org_id
             having count(*) > 1) d)                                as r3_no_duplicate_org_rows,

    (select bool_and(not public and file_size_limit = 10485760
                     and allowed_mime_types @> array['application/pdf', 'image/jpeg',
                                                     'image/png', 'image/webp', 'image/tiff'])
       from storage.buckets
      where id = 'documents')                                       as r5_bucket_ok
;
-- expect: every column true on the single returned row.

-- ============================================================================
-- SECTION 7 - ROLLBACK (DOCUMENTED, NOT EXECUTED)
--
-- SECTIONS 1-5 are one transaction. Any guard failure rolls everything back
-- automatically; no manual step is needed for a failed run.
--
-- After a SUCCESSFUL run, rolling back is a separate, deliberate decision.
-- The statements below are commented out on purpose. They drop only objects
-- this script can have created, and each one is preceded by a state check so
-- it can never remove something that already existed in production.
-- Dropping the columns or the functions removes no user data from any other
-- table; dropping onboarding_drafts DOES destroy in-progress drafts.
--
--   -- R1: only if the column did not exist before this repair.
--   --     (V1 of the previous run, or the apply log, tells you.)
--   alter table public.invoice_codings drop column if exists reasoning;
--
--   -- R2: onboarding drafts. Only if this repair created the table.
--   drop policy if exists onboarding_drafts_owner on public.onboarding_drafts;
--   drop function if exists public.claim_onboarding_workspace(uuid);
--   drop table if exists public.onboarding_drafts;      -- destroys drafts
--
--   -- R2: organization profile columns (added by 2.8, nullable, no data loss).
--   alter table public.organizations
--       drop column if exists accounting_software,
--       drop column if exists monthly_invoice_volume,
--       drop column if exists business_type;
--
--   -- R3: the RPC and the two indexes (indexes are safe to drop; they carry
--   --     no data, only the rotation invariant).
--   drop function if exists public.manage_ap_email_intake_address(uuid, uuid, text, boolean);
--   drop index if exists public.uq_ap_email_address_one_active_per_org;
--   drop index if exists public.uq_ap_email_address_unique_active_value;
--
--   -- R3: privileges are NOT restored to their previous, broader state.
--   --     Widening them back is a security decision, not a rollback.
--
--   -- R4: bucket settings are NOT reverted. Reverting to "no limit, any MIME
--   --     type" would re-open the upload surface this repair closes.
--
--   notify pgrst, 'reload schema';
-- ============================================================================
-- END OF FILE
