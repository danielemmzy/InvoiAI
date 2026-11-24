-- Ticket 21 (step 0): organization-scoped purchase order numbers.
--
-- A manual PO needs a number even when no accounting provider is connected, and
-- an imported PO needs a stable internal reference that does not depend on the
-- provider's own numbering. `purchase_orders.po_number` stays as the
-- provider/organization supplied number. `purchase_orders.org_number` is the
-- InvoiAI-assigned, per-organization number ("PO-000001").
--
-- Additive and idempotent. Safe to run more than once.
--
-- This migration must run before:
--   20261110_purchase_order_lines_and_atomic_receipts.sql
--   20261111_document_match_allocations.sql

-- ---------------------------------------------------------------------------
-- 1. Per-organization number series
-- ---------------------------------------------------------------------------

create table if not exists public.purchase_order_number_counters (
    org_id uuid primary key references public.organizations(id) on delete cascade,
    prefix text not null default 'PO',
    last_number bigint not null default 0,
    updated_at timestamptz not null default now()
);

comment on table public.purchase_order_number_counters is
    'Per-organization counter behind purchase_orders.org_number. One row per organization.';

-- ---------------------------------------------------------------------------
-- 2. Number generator
-- ---------------------------------------------------------------------------

create or replace function public.next_purchase_order_org_number(p_org_id uuid)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
    v_prefix text;
    v_next bigint;
begin
    if p_org_id is null then
        raise exception 'ORG_ID_REQUIRED' using errcode = 'P0001';
    end if;

    -- The upsert is atomic: concurrent inserts for the same organization
    -- serialize on the primary key instead of handing out the same number.
    insert into public.purchase_order_number_counters (org_id, last_number)
    values (p_org_id, 1)
    on conflict (org_id) do update
        set last_number = public.purchase_order_number_counters.last_number + 1,
            updated_at = now()
    returning prefix, last_number into v_prefix, v_next;

    return v_prefix || '-' || lpad(v_next::text, 6, '0');
end;
$$;

-- ---------------------------------------------------------------------------
-- 3. Column, uniqueness, and automatic assignment
-- ---------------------------------------------------------------------------

alter table public.purchase_orders
    add column if not exists org_number text;

comment on column public.purchase_orders.org_number is
    'InvoiAI-assigned per-organization PO number. Unique within the organization; independent of the provider po_number.';

create unique index if not exists uq_purchase_orders_org_org_number
    on public.purchase_orders (org_id, org_number)
    where org_number is not null;

create or replace function public.assign_purchase_order_org_number()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if new.org_number is null or btrim(new.org_number) = '' then
        new.org_number := public.next_purchase_order_org_number(new.org_id);
    end if;
    return new;
end;
$$;

drop trigger if exists trg_purchase_orders_org_number on public.purchase_orders;
create trigger trg_purchase_orders_org_number
    before insert on public.purchase_orders
    for each row
    execute function public.assign_purchase_order_org_number();

-- ---------------------------------------------------------------------------
-- 4. Backfill existing rows
-- ---------------------------------------------------------------------------

-- Deterministic order so a re-run assigns the same sequence to the same rows.
-- Existing rows keep their provider po_number; org_number is added alongside it.
do $$
declare
    r record;
begin
    for r in
        select id, org_id
          from public.purchase_orders
         where org_number is null
         order by org_id, created_at nulls last, id
    loop
        update public.purchase_orders
           set org_number = public.next_purchase_order_org_number(r.org_id)
         where id = r.id;
    end loop;
end $$;

-- ---------------------------------------------------------------------------
-- 5. Access
-- ---------------------------------------------------------------------------

alter table public.purchase_order_number_counters enable row level security;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'purchase_order_number_counters'
          and policyname = 'purchase_order_number_counters_org_member'
    ) then
        create policy purchase_order_number_counters_org_member
            on public.purchase_order_number_counters
            for select to authenticated
            using (exists (
                select 1 from public.org_members m
                where m.org_id = purchase_order_number_counters.org_id
                  and m.user_id = auth.uid()
                  and m.is_active = true
            ));
    end if;
end $$;

revoke all on function public.next_purchase_order_org_number(uuid) from public, anon, authenticated;
grant execute on function public.next_purchase_order_org_number(uuid) to service_role;
