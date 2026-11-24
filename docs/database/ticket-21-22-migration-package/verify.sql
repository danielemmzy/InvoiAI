-- Verification for the ticket 21/22 migration package.
-- Read-only. Safe to run any time; changes nothing.
--
-- Run this AFTER the three migrations, in the same Supabase SQL Editor.
-- Every row must show status = 'OK'. The first block is informational only.

-- ---------------------------------------------------------------------------
-- 0. Informational: what the migration history table knows about.
--    This package is applied manually, so it may not appear there at all.
-- ---------------------------------------------------------------------------
do $$
declare
    v_rows text;
begin
    if to_regclass('supabase_migrations.schema_migrations') is null then
        raise notice 'migration history table not present; skipping';
        return;
    end if;

    execute
        'select string_agg(version || '' '' || coalesce(name, ''''), E''\n'' order by version)
           from supabase_migrations.schema_migrations
          where version like ''2026111%''
             or name like ''%purchase_order%''
             or name like ''%document_match_allocations%'''
    into v_rows;

    raise notice E'migration history matches:\n%', coalesce(v_rows, '(none)');
end $$;

-- ---------------------------------------------------------------------------
-- 1. Structure and guard checks
-- ---------------------------------------------------------------------------
with checks (check_id, description, ok, detail) as (
    select 1, 'table purchase_order_number_counters',
           to_regclass('public.purchase_order_number_counters') is not null,
           coalesce(to_regclass('public.purchase_order_number_counters')::text, 'missing')

    union all
    select 2, 'column purchase_orders.org_number',
           exists (select 1 from information_schema.columns
                    where table_schema = 'public' and table_name = 'purchase_orders'
                      and column_name = 'org_number'),
           'added by 20261110_purchase_order_00_org_number.sql'

    union all
    select 3, 'unique index uq_purchase_orders_org_org_number',
           exists (select 1 from pg_indexes
                    where schemaname = 'public' and indexname = 'uq_purchase_orders_org_org_number'),
           'one org_number per organization'

    union all
    select 4, 'function next_purchase_order_org_number',
           to_regprocedure('public.next_purchase_order_org_number(uuid)') is not null,
           'per-organization number generator'

    union all
    select 5, 'trigger trg_purchase_orders_org_number',
           exists (select 1 from pg_trigger where tgname = 'trg_purchase_orders_org_number'
                      and not tgisinternal),
           'assigns org_number on insert'

    union all
    select 6, 'table purchase_order_lines',
           to_regclass('public.purchase_order_lines') is not null,
           'created only if it did not already exist'

    union all
    select 7, 'purchase_order_lines canonical columns',
           (select count(*) = 5 from information_schema.columns
             where table_schema = 'public' and table_name = 'purchase_order_lines'
               and column_name in ('org_id', 'purchase_order_id', 'line_number', 'quantity', 'unit_price')),
           'org_id, purchase_order_id, line_number, quantity, unit_price'

    union all
    select 8, 'goods_receipts void metadata',
           (select count(*) = 3 from information_schema.columns
             where table_schema = 'public' and table_name = 'goods_receipts'
               and column_name in ('voided_at', 'voided_by', 'void_reason')),
           'voided_at, voided_by, void_reason'

    union all
    select 9, 'function record_goods_receipt',
           to_regprocedure('public.record_goods_receipt(uuid,uuid,jsonb,jsonb)') is not null,
           'atomic header + lines'

    union all
    select 10, 'function void_goods_receipt',
           to_regprocedure('public.void_goods_receipt(uuid,uuid,text,uuid)') is not null,
           'requires a reason'

    union all
    select 11, 'table document_match_allocations',
           to_regclass('public.document_match_allocations') is not null,
           'line-level match authority'

    union all
    select 12, 'unique index uq_document_match_allocations_active_key',
           exists (select 1 from pg_indexes
                    where schemaname = 'public' and indexname = 'uq_document_match_allocations_active_key'),
           'one active allocation per invoice/PO/receipt line'

    union all
    select 13, 'allocation guard trigger',
           exists (select 1 from pg_trigger where tgname = 'trg_document_match_allocations_guard'
                      and not tgisinternal),
           'tenancy, ownership, over-allocation'

    union all
    select 14, 'allocated receipt guards',
           (select count(*) = 2 from pg_trigger
             where tgname in ('trg_goods_receipts_allocated_guard',
                              'trg_goods_receipt_lines_allocated_guard')
               and not tgisinternal),
           'allocated evidence cannot be silently edited'

    union all
    select 15, 'function purchase_order_line_balances',
           to_regprocedure('public.purchase_order_line_balances(uuid,uuid)') is not null,
           'ordered / received / allocated / remaining'

    union all
    select 16, 'RLS enabled on new tables',
           (select count(*) = 3 from pg_class c
              join pg_namespace n on n.oid = c.relnamespace
             where n.nspname = 'public'
               and c.relname in ('purchase_order_number_counters',
                                 'purchase_order_lines',
                                 'document_match_allocations')
               and c.relrowsecurity),
           'purchase_order_number_counters, purchase_order_lines, document_match_allocations'
)
select
    check_id,
    case when ok then 'OK' else 'FAIL' end as status,
    description,
    detail
  from checks
 order by check_id;

-- ---------------------------------------------------------------------------
-- 2. Privilege check (guarded: the functions must exist first).
-- ---------------------------------------------------------------------------
do $$
declare
    v_ok boolean;
begin
    if to_regprocedure('public.record_goods_receipt(uuid,uuid,jsonb,jsonb)') is null
       or to_regprocedure('public.void_goods_receipt(uuid,uuid,text,uuid)') is null then
        raise notice 'FAIL 17 write RPCs are service_role only: functions are missing';
        return;
    end if;

    select
        not has_function_privilege('authenticated', 'public.record_goods_receipt(uuid,uuid,jsonb,jsonb)', 'execute')
        and not has_function_privilege('authenticated', 'public.void_goods_receipt(uuid,uuid,text,uuid)', 'execute')
        and not has_function_privilege('anon', 'public.record_goods_receipt(uuid,uuid,jsonb,jsonb)', 'execute')
      into v_ok;

    if v_ok then
        raise notice 'OK   17 write RPCs are service_role only';
    else
        raise notice 'FAIL 17 a write RPC is executable by authenticated or anon';
    end if;
end $$;

-- ---------------------------------------------------------------------------
-- 3. Data check: the backfill in migration 1 must have covered every row.
--    Guarded because it reads a column that migration 1 adds.
-- ---------------------------------------------------------------------------
do $$
declare
    v_nulls bigint;
begin
    if not exists (
        select 1 from information_schema.columns
         where table_schema = 'public'
           and table_name = 'purchase_orders'
           and column_name = 'org_number'
    ) then
        raise notice 'FAIL 18 every purchase order has an org_number: column is missing';
        return;
    end if;

    execute 'select count(*) from public.purchase_orders where org_number is null'
       into v_nulls;

    if v_nulls = 0 then
        raise notice 'OK   18 every purchase order has an org_number';
    else
        raise notice 'FAIL 18 % purchase order(s) still have a null org_number', v_nulls;
    end if;
end $$;
