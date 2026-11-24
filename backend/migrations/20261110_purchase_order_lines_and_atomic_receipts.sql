-- Ticket 21: purchase order lines and atomic goods receipts.
--
-- Delivers the data + write path for:
--   * manual or CSV POs with line-level quantities
--   * partial goods receipts that accumulate against a PO line
--   * receipt voiding that requires a reason
--
-- Additive and idempotent. Safe to run more than once.
--
-- Depends on: 20261110_purchase_order_00_org_number.sql
-- Must run before: 20261111_document_match_allocations.sql
--
-- `purchase_order_lines` predates the migration manifest in some environments,
-- so the table is created only when missing and every column is then added with
-- `if not exists`. Constraints that could fail on legacy data are created as
-- indexes, not as hard table constraints.

-- ---------------------------------------------------------------------------
-- 1. Purchase order lines
-- ---------------------------------------------------------------------------

create table if not exists public.purchase_order_lines (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references public.organizations(id) on delete cascade,
    purchase_order_id uuid not null references public.purchase_orders(id) on delete cascade,
    line_number integer,
    description text,
    sku text,
    unit_of_measure text,
    quantity numeric(18, 4) not null default 0,
    unit_price numeric(18, 4) not null default 0,
    amount numeric(18, 4) not null default 0,
    tax_rate numeric(9, 4),
    tax_amount numeric(18, 4),
    currency text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.purchase_order_lines
    add column if not exists org_id uuid,
    add column if not exists purchase_order_id uuid,
    add column if not exists line_number integer,
    add column if not exists description text,
    add column if not exists sku text,
    add column if not exists unit_of_measure text,
    add column if not exists quantity numeric(18, 4),
    add column if not exists unit_price numeric(18, 4),
    add column if not exists amount numeric(18, 4),
    add column if not exists tax_rate numeric(9, 4),
    add column if not exists tax_amount numeric(18, 4),
    add column if not exists currency text,
    add column if not exists metadata jsonb default '{}'::jsonb,
    add column if not exists created_at timestamptz default now(),
    add column if not exists updated_at timestamptz default now();

comment on table public.purchase_order_lines is
    'Ordered PO lines. Received quantity is derived from confirmed goods receipt lines, never stored here.';

create index if not exists idx_purchase_order_lines_org_order
    on public.purchase_order_lines (org_id, purchase_order_id);

-- Keeps CSV/import retries from duplicating the same line twice.
create unique index if not exists uq_purchase_order_lines_order_line_number
    on public.purchase_order_lines (purchase_order_id, line_number)
    where line_number is not null;

-- ---------------------------------------------------------------------------
-- 2. Goods receipt void metadata
-- ---------------------------------------------------------------------------

alter table public.goods_receipts
    add column if not exists voided_at timestamptz,
    add column if not exists voided_by uuid,
    add column if not exists void_reason text;

comment on column public.goods_receipts.void_reason is
    'Required when a receipt is voided. Voiding never rewrites an existing invoice allocation.';

-- Idempotent CSV/API import key.
create unique index if not exists uq_goods_receipts_org_external
    on public.goods_receipts (org_id, external_id)
    where external_id is not null;

create index if not exists idx_goods_receipts_org_po_status
    on public.goods_receipts (org_id, purchase_order_id, status);

create index if not exists idx_goods_receipt_lines_po_line
    on public.goods_receipt_lines (purchase_order_line_id)
    where purchase_order_line_id is not null;

-- ---------------------------------------------------------------------------
-- 3. Atomic receipt recording
-- ---------------------------------------------------------------------------

-- One transaction for header + lines. PostgREST cannot batch these safely on
-- its own, so the write path is a single function call.
create or replace function public.record_goods_receipt(
    p_org_id uuid,
    p_purchase_order_id uuid,
    p_receipt jsonb,
    p_lines jsonb
) returns public.goods_receipts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_po public.purchase_orders%rowtype;
    v_receipt public.goods_receipts%rowtype;
    v_existing public.goods_receipts%rowtype;
    v_status text;
    v_line jsonb;
    v_line_id uuid;
    v_received numeric;
    v_accepted numeric;
    v_rejected numeric;
    v_count integer := 0;
begin
    if p_org_id is null or p_purchase_order_id is null then
        raise exception 'ORG_AND_PURCHASE_ORDER_REQUIRED' using errcode = 'P0001';
    end if;

    if p_lines is null or jsonb_typeof(p_lines) <> 'array' or jsonb_array_length(p_lines) = 0 then
        raise exception 'RECEIPT_LINES_REQUIRED' using errcode = 'P0001';
    end if;

    select * into v_po
      from public.purchase_orders
     where id = p_purchase_order_id
       and org_id = p_org_id;

    if not found then
        raise exception 'PURCHASE_ORDER_NOT_FOUND' using errcode = 'P0002';
    end if;

    if coalesce(lower(v_po.status), '') in ('cancelled', 'canceled', 'closed', 'void', 'voided') then
        raise exception 'PURCHASE_ORDER_NOT_RECEIVABLE' using errcode = 'P0001';
    end if;

    v_status := coalesce(nullif(btrim(p_receipt ->> 'status'), ''), 'draft');
    if v_status not in ('draft', 'confirmed', 'complete') then
        raise exception 'INVALID_RECEIPT_STATUS' using errcode = 'P0001';
    end if;

    -- Idempotent retry: the same external reference returns the stored receipt.
    if nullif(btrim(p_receipt ->> 'external_id'), '') is not null then
        select * into v_existing
          from public.goods_receipts
         where org_id = p_org_id
           and external_id = btrim(p_receipt ->> 'external_id');

        if found then
            return v_existing;
        end if;
    end if;

    insert into public.goods_receipts (
        org_id,
        purchase_order_id,
        vendor_id,
        receipt_number,
        received_at,
        received_by,
        location_id,
        status,
        source,
        external_id,
        notes
    ) values (
        p_org_id,
        p_purchase_order_id,
        coalesce(nullif(btrim(p_receipt ->> 'vendor_id'), '')::uuid, v_po.vendor_id),
        nullif(btrim(p_receipt ->> 'receipt_number'), ''),
        coalesce(nullif(btrim(p_receipt ->> 'received_at'), '')::timestamptz, now()),
        nullif(btrim(p_receipt ->> 'received_by'), '')::uuid,
        nullif(btrim(p_receipt ->> 'location_id'), '')::uuid,
        v_status,
        coalesce(nullif(btrim(p_receipt ->> 'source'), ''), 'manual'),
        nullif(btrim(p_receipt ->> 'external_id'), ''),
        nullif(btrim(p_receipt ->> 'notes'), '')
    )
    returning * into v_receipt;

    for v_line in select * from jsonb_array_elements(p_lines)
    loop
        v_line_id := nullif(btrim(v_line ->> 'purchase_order_line_id'), '')::uuid;
        v_received := nullif(btrim(v_line ->> 'quantity_received'), '')::numeric;
        v_accepted := nullif(btrim(v_line ->> 'quantity_accepted'), '')::numeric;
        v_rejected := coalesce(nullif(btrim(v_line ->> 'quantity_rejected'), '')::numeric, 0);

        if v_received is null or v_received <= 0 then
            raise exception 'RECEIPT_LINE_QUANTITY_INVALID' using errcode = 'P0001';
        end if;

        if v_rejected < 0 then
            raise exception 'RECEIPT_LINE_QUANTITY_INVALID' using errcode = 'P0001';
        end if;

        if v_accepted is not null and (v_accepted < 0 or v_accepted > v_received) then
            raise exception 'RECEIPT_LINE_ACCEPTED_INVALID' using errcode = 'P0001';
        end if;

        if v_line_id is not null and not exists (
            select 1
              from public.purchase_order_lines pol
             where pol.id = v_line_id
               and pol.purchase_order_id = p_purchase_order_id
        ) then
            raise exception 'PO_LINE_NOT_IN_PURCHASE_ORDER' using errcode = 'P0001';
        end if;

        insert into public.goods_receipt_lines (
            goods_receipt_id,
            purchase_order_line_id,
            description,
            sku,
            quantity_ordered,
            quantity_received,
            quantity_accepted,
            quantity_rejected,
            unit_of_measure,
            unit_price,
            warehouse_location,
            notes
        ) values (
            v_receipt.id,
            v_line_id,
            nullif(btrim(v_line ->> 'description'), ''),
            nullif(btrim(v_line ->> 'sku'), ''),
            nullif(btrim(v_line ->> 'quantity_ordered'), '')::numeric,
            v_received,
            coalesce(v_accepted, v_received),
            v_rejected,
            nullif(btrim(v_line ->> 'unit_of_measure'), ''),
            nullif(btrim(v_line ->> 'unit_price'), '')::numeric,
            nullif(btrim(v_line ->> 'warehouse_location'), ''),
            nullif(btrim(v_line ->> 'notes'), '')
        );

        v_count := v_count + 1;
    end loop;

    if v_count = 0 then
        raise exception 'RECEIPT_LINES_REQUIRED' using errcode = 'P0001';
    end if;

    return v_receipt;
end;
$$;

comment on function public.record_goods_receipt(uuid, uuid, jsonb, jsonb) is
    'Records a goods receipt and its lines in one transaction. Idempotent on (org_id, external_id).';

-- ---------------------------------------------------------------------------
-- 4. Receipt void
-- ---------------------------------------------------------------------------

create or replace function public.void_goods_receipt(
    p_org_id uuid,
    p_receipt_id uuid,
    p_reason text,
    p_actor_id uuid default null
) returns public.goods_receipts
language plpgsql
security definer
set search_path = public
as $$
declare
    v_receipt public.goods_receipts%rowtype;
    v_reason text := nullif(btrim(p_reason), '');
begin
    if v_reason is null then
        raise exception 'VOID_REASON_REQUIRED' using errcode = 'P0001';
    end if;

    select * into v_receipt
      from public.goods_receipts
     where id = p_receipt_id
       and org_id = p_org_id
     for update;

    if not found then
        raise exception 'RECEIPT_NOT_FOUND' using errcode = 'P0002';
    end if;

    if lower(v_receipt.status) = 'voided' then
        raise exception 'RECEIPT_ALREADY_VOIDED' using errcode = 'P0001';
    end if;

    update public.goods_receipts
       set status = 'voided',
           void_reason = v_reason,
           voided_by = p_actor_id,
           voided_at = now(),
           updated_at = now()
     where id = p_receipt_id
     returning * into v_receipt;

    -- Append-only audit event. Voiding a receipt does not touch an invoice
    -- allocation; the matching service re-runs and records the consequence.
    if to_regclass('public.audit_logs') is not null then
        execute
            'insert into public.audit_logs '
            '(org_id, user_id, action, resource_type, resource_id, '
            ' old_values, new_values, diff, metadata, ai_triggered) '
            'values ($1, $2, $3, $4, $5, $6, $7, $8, $9, false)'
        using
            p_org_id,
            p_actor_id,
            'goods_receipt.voided',
            'goods_receipt',
            p_receipt_id,
            jsonb_build_object('status', v_receipt.status),
            jsonb_build_object('status', 'voided', 'void_reason', v_reason),
            '{}'::jsonb,
            jsonb_build_object('void_reason', v_reason);
    end if;

    return v_receipt;
end;
$$;

comment on function public.void_goods_receipt(uuid, uuid, text, uuid) is
    'Voids a goods receipt. Requires a reason and writes an audit event.';

-- ---------------------------------------------------------------------------
-- 5. Access
-- ---------------------------------------------------------------------------

alter table public.purchase_order_lines enable row level security;

do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name = 'purchase_order_lines'
          and column_name = 'org_id'
    ) and not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'purchase_order_lines'
          and policyname = 'purchase_order_lines_org_member'
    ) then
        create policy purchase_order_lines_org_member
            on public.purchase_order_lines
            for all to authenticated
            using (exists (
                select 1 from public.org_members m
                where m.org_id = purchase_order_lines.org_id
                  and m.user_id = auth.uid()
                  and m.is_active = true
            ))
            with check (exists (
                select 1 from public.org_members m
                where m.org_id = purchase_order_lines.org_id
                  and m.user_id = auth.uid()
                  and m.is_active = true
            ));
    end if;
end $$;

revoke all on function public.record_goods_receipt(uuid, uuid, jsonb, jsonb) from public, anon, authenticated;
revoke all on function public.void_goods_receipt(uuid, uuid, text, uuid) from public, anon, authenticated;
grant execute on function public.record_goods_receipt(uuid, uuid, jsonb, jsonb) to service_role;
grant execute on function public.void_goods_receipt(uuid, uuid, text, uuid) to service_role;
