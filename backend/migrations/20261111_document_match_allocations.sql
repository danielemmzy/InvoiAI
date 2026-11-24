-- Ticket 22: persisted line-level invoice match allocations.
--
-- Delivers the data + guards for:
--   * one invoice allocated across zero, one, or many POs and receipts
--   * partial invoices and partial deliveries
--   * over-allocation blocked at the database boundary
--   * allocated receipts that cannot be silently edited
--
-- Additive and idempotent. Safe to run more than once.
--
-- Depends on: 20261110_purchase_order_00_org_number.sql
--             20261110_purchase_order_lines_and_atomic_receipts.sql
--
-- `documents.purchase_order_id` / `documents.goods_receipt_id` stay as a
-- convenience "primary" reference. This table is the authority for matching.

-- ---------------------------------------------------------------------------
-- 1. Allocation table
-- ---------------------------------------------------------------------------

create table if not exists public.document_match_allocations (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references public.organizations(id) on delete cascade,
    document_id uuid not null,
    line_item_id uuid,
    purchase_order_id uuid not null,
    purchase_order_line_id uuid,
    goods_receipt_id uuid,
    goods_receipt_line_id uuid,
    allocated_quantity numeric(18, 4) not null default 0,
    allocated_amount numeric(18, 4) not null default 0,
    currency text not null,
    status text not null default 'allocated',
    match_mode text,
    created_by uuid,
    void_reason text,
    voided_by uuid,
    voided_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint document_match_allocations_status_check
        check (status in ('allocated', 'voided')),
    constraint document_match_allocations_quantity_check
        check (allocated_quantity >= 0),
    constraint document_match_allocations_amount_check
        check (allocated_amount >= 0)
);

comment on table public.document_match_allocations is
    'Line-level invoice allocation to PO and receipt lines. Voided rows are kept for audit; active rows are the match authority.';

-- The currency is inherited from the PO by the guard trigger. A column default
-- would be applied before the trigger runs and would mask that inheritance.
alter table public.document_match_allocations
    alter column currency drop default;

-- One active allocation per invoice line + PO line + receipt line.
-- NULLs are collapsed so the key still holds when a receipt is not involved.
create unique index if not exists uq_document_match_allocations_active_key
    on public.document_match_allocations (
        org_id,
        coalesce(line_item_id, '00000000-0000-0000-0000-000000000000'::uuid),
        coalesce(purchase_order_line_id, '00000000-0000-0000-0000-000000000000'::uuid),
        coalesce(goods_receipt_line_id, '00000000-0000-0000-0000-000000000000'::uuid)
    )
    where status = 'allocated';

create index if not exists idx_document_match_allocations_org_document
    on public.document_match_allocations (org_id, document_id)
    where status = 'allocated';

create index if not exists idx_document_match_allocations_org_po
    on public.document_match_allocations (org_id, purchase_order_id)
    where status = 'allocated';

create index if not exists idx_document_match_allocations_receipt
    on public.document_match_allocations (goods_receipt_id)
    where goods_receipt_id is not null;

-- ---------------------------------------------------------------------------
-- 2. Allocation guard: tenancy, ownership, and over-allocation
-- ---------------------------------------------------------------------------

create or replace function public.enforce_document_match_allocation()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    v_po_org uuid;
    v_po_currency text;
    v_doc_org uuid;
    v_line_doc uuid;
    v_line_qty numeric;
    v_pol_po uuid;
    v_pol_qty numeric;
    v_receipt_org uuid;
    v_receipt_po uuid;
    v_receipt_status text;
    v_grl_receipt uuid;
    v_grl_qty numeric;
    v_used numeric;
begin
    new.updated_at := now();
    new.created_at := coalesce(new.created_at, now());

    if new.status = 'voided' then
        if nullif(btrim(new.void_reason), '') is null then
            raise exception 'VOID_REASON_REQUIRED' using errcode = 'P0001';
        end if;
        new.voided_at := coalesce(new.voided_at, now());
        return new;
    end if;

    if new.allocated_quantity is null or new.allocated_quantity <= 0 then
        raise exception 'ALLOCATION_QUANTITY_INVALID' using errcode = 'P0001';
    end if;

    if new.allocated_amount is null or new.allocated_amount < 0 then
        raise exception 'ALLOCATION_AMOUNT_INVALID' using errcode = 'P0001';
    end if;

    if new.purchase_order_id is null then
        raise exception 'ALLOCATION_PURCHASE_ORDER_REQUIRED' using errcode = 'P0001';
    end if;

    if new.document_id is null then
        raise exception 'ALLOCATION_DOCUMENT_REQUIRED' using errcode = 'P0001';
    end if;

    select po.org_id, po.currency into v_po_org, v_po_currency
      from public.purchase_orders po
     where po.id = new.purchase_order_id;

    if not found then
        raise exception 'PURCHASE_ORDER_NOT_FOUND' using errcode = 'P0002';
    end if;

    if v_po_org <> new.org_id then
        raise exception 'PURCHASE_ORDER_NOT_IN_ORG' using errcode = 'P0001';
    end if;

    new.currency := coalesce(nullif(btrim(new.currency), ''), v_po_currency, 'USD');

    select d.org_id into v_doc_org
      from public.documents d
     where d.id = new.document_id;

    if not found then
        raise exception 'DOCUMENT_NOT_FOUND' using errcode = 'P0002';
    end if;

    if v_doc_org <> new.org_id then
        raise exception 'DOCUMENT_NOT_IN_ORG' using errcode = 'P0001';
    end if;

    -- Serialize concurrent allocation for this invoice and this PO.
    -- Always the same order, so two writers cannot deadlock each other.
    perform pg_advisory_xact_lock(hashtext('dma-document:' || new.document_id::text));
    perform pg_advisory_xact_lock(hashtext('dma-po:' || new.purchase_order_id::text));

    if new.goods_receipt_line_id is not null then
        select grl.goods_receipt_id,
               coalesce(grl.quantity_accepted, grl.quantity_received)
          into v_grl_receipt, v_grl_qty
          from public.goods_receipt_lines grl
         where grl.id = new.goods_receipt_line_id;

        if not found then
            raise exception 'RECEIPT_LINE_NOT_FOUND' using errcode = 'P0002';
        end if;

        if new.goods_receipt_id is null then
            new.goods_receipt_id := v_grl_receipt;
        elsif new.goods_receipt_id <> v_grl_receipt then
            raise exception 'RECEIPT_LINE_NOT_IN_RECEIPT' using errcode = 'P0001';
        end if;
    end if;

    if new.goods_receipt_id is not null then
        select gr.org_id, gr.purchase_order_id, gr.status
          into v_receipt_org, v_receipt_po, v_receipt_status
          from public.goods_receipts gr
         where gr.id = new.goods_receipt_id;

        if not found then
            raise exception 'RECEIPT_NOT_FOUND' using errcode = 'P0002';
        end if;

        if v_receipt_org <> new.org_id then
            raise exception 'RECEIPT_NOT_IN_ORG' using errcode = 'P0001';
        end if;

        if v_receipt_po is not null and v_receipt_po <> new.purchase_order_id then
            raise exception 'RECEIPT_NOT_IN_PURCHASE_ORDER' using errcode = 'P0001';
        end if;

        if lower(coalesce(v_receipt_status, '')) = 'voided' then
            raise exception 'RECEIPT_VOIDED' using errcode = 'P0001';
        end if;
    end if;

    if new.line_item_id is not null then
        select dli.document_id, dli.quantity
          into v_line_doc, v_line_qty
          from public.document_line_items dli
         where dli.id = new.line_item_id;

        if not found then
            raise exception 'INVOICE_LINE_NOT_FOUND' using errcode = 'P0002';
        end if;

        if v_line_doc <> new.document_id then
            raise exception 'INVOICE_LINE_NOT_IN_DOCUMENT' using errcode = 'P0001';
        end if;

        select coalesce(sum(a.allocated_quantity), 0) into v_used
          from public.document_match_allocations a
         where a.line_item_id = new.line_item_id
           and a.status = 'allocated'
           and a.id <> coalesce(new.id, '00000000-0000-0000-0000-000000000000'::uuid);

        if v_line_qty is not null and v_used + new.allocated_quantity > v_line_qty then
            raise exception 'INVOICE_LINE_OVER_ALLOCATED' using errcode = 'P0001';
        end if;
    end if;

    if new.purchase_order_line_id is not null then
        select pol.purchase_order_id, pol.quantity
          into v_pol_po, v_pol_qty
          from public.purchase_order_lines pol
         where pol.id = new.purchase_order_line_id;

        if not found then
            raise exception 'PO_LINE_NOT_FOUND' using errcode = 'P0002';
        end if;

        if v_pol_po <> new.purchase_order_id then
            raise exception 'PO_LINE_NOT_IN_PURCHASE_ORDER' using errcode = 'P0001';
        end if;

        select coalesce(sum(a.allocated_quantity), 0) into v_used
          from public.document_match_allocations a
         where a.purchase_order_line_id = new.purchase_order_line_id
           and a.status = 'allocated'
           and a.id <> coalesce(new.id, '00000000-0000-0000-0000-000000000000'::uuid);

        if v_pol_qty is not null and v_used + new.allocated_quantity > v_pol_qty then
            raise exception 'PO_LINE_OVER_ALLOCATED' using errcode = 'P0001';
        end if;
    end if;

    if new.goods_receipt_line_id is not null then
        select coalesce(sum(a.allocated_quantity), 0) into v_used
          from public.document_match_allocations a
         where a.goods_receipt_line_id = new.goods_receipt_line_id
           and a.status = 'allocated'
           and a.id <> coalesce(new.id, '00000000-0000-0000-0000-000000000000'::uuid);

        if v_grl_qty is not null and v_used + new.allocated_quantity > v_grl_qty then
            raise exception 'RECEIPT_LINE_OVER_ALLOCATED' using errcode = 'P0001';
        end if;
    end if;

    return new;
end;
$$;

drop trigger if exists trg_document_match_allocations_guard on public.document_match_allocations;
create trigger trg_document_match_allocations_guard
    before insert or update on public.document_match_allocations
    for each row
    execute function public.enforce_document_match_allocation();

-- ---------------------------------------------------------------------------
-- 3. An allocated receipt cannot be silently edited
-- ---------------------------------------------------------------------------

create or replace function public.guard_allocated_goods_receipt_line()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if exists (
        select 1
          from public.document_match_allocations a
         where a.goods_receipt_line_id = old.id
           and a.status = 'allocated'
    ) then
        raise exception 'ALLOCATED_RECEIPT_LINE_IMMUTABLE' using errcode = 'P0001';
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end;
$$;

drop trigger if exists trg_goods_receipt_lines_allocated_guard on public.goods_receipt_lines;
create trigger trg_goods_receipt_lines_allocated_guard
    before update or delete on public.goods_receipt_lines
    for each row
    execute function public.guard_allocated_goods_receipt_line();

create or replace function public.guard_allocated_goods_receipt()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    v_allocated boolean;
begin
    select exists (
        select 1
          from public.document_match_allocations a
         where a.goods_receipt_id = old.id
           and a.status = 'allocated'
    ) into v_allocated;

    if tg_op = 'DELETE' then
        if v_allocated then
            raise exception 'ALLOCATED_RECEIPT_IMMUTABLE' using errcode = 'P0001';
        end if;
        return old;
    end if;

    if v_allocated
       and (
           new.purchase_order_id is distinct from old.purchase_order_id
           or new.org_id is distinct from old.org_id
       ) then
        raise exception 'ALLOCATED_RECEIPT_IMMUTABLE' using errcode = 'P0001';
    end if;

    if lower(coalesce(new.status, '')) = 'voided'
       and lower(coalesce(old.status, '')) <> 'voided' then
        if nullif(btrim(new.void_reason), '') is null then
            raise exception 'VOID_REASON_REQUIRED' using errcode = 'P0001';
        end if;
        new.voided_at := coalesce(new.voided_at, now());
    end if;

    return new;
end;
$$;

drop trigger if exists trg_goods_receipts_allocated_guard on public.goods_receipts;
create trigger trg_goods_receipts_allocated_guard
    before update or delete on public.goods_receipts
    for each row
    execute function public.guard_allocated_goods_receipt();

-- ---------------------------------------------------------------------------
-- 4. Remaining quantity and amount per PO line
-- ---------------------------------------------------------------------------

create or replace function public.purchase_order_line_balances(
    p_org_id uuid,
    p_purchase_order_id uuid
) returns table (
    purchase_order_line_id uuid,
    line_number integer,
    description text,
    quantity_ordered numeric,
    quantity_received numeric,
    quantity_allocated numeric,
    quantity_remaining numeric,
    amount_ordered numeric,
    amount_allocated numeric,
    amount_remaining numeric
)
language sql
stable
security definer
set search_path = public
as $$
    with received as (
        select grl.purchase_order_line_id,
               sum(grl.quantity_received) as quantity_received
          from public.goods_receipt_lines grl
          join public.goods_receipts gr on gr.id = grl.goods_receipt_id
         where gr.org_id = p_org_id
           and gr.purchase_order_id = p_purchase_order_id
           and gr.status in ('confirmed', 'complete')
         group by grl.purchase_order_line_id
    ),
    allocated as (
        select a.purchase_order_line_id,
               sum(a.allocated_quantity) as quantity_allocated,
               sum(a.allocated_amount) as amount_allocated
          from public.document_match_allocations a
         where a.org_id = p_org_id
           and a.purchase_order_id = p_purchase_order_id
           and a.status = 'allocated'
         group by a.purchase_order_line_id
    )
    select pol.id,
           pol.line_number,
           pol.description,
           coalesce(pol.quantity, 0),
           coalesce(received.quantity_received, 0),
           coalesce(allocated.quantity_allocated, 0),
           coalesce(pol.quantity, 0) - coalesce(allocated.quantity_allocated, 0),
           coalesce(pol.amount, 0),
           coalesce(allocated.amount_allocated, 0),
           coalesce(pol.amount, 0) - coalesce(allocated.amount_allocated, 0)
      from public.purchase_order_lines pol
      left join received on received.purchase_order_line_id = pol.id
      left join allocated on allocated.purchase_order_line_id = pol.id
     where pol.org_id = p_org_id
       and pol.purchase_order_id = p_purchase_order_id
     order by pol.line_number nulls last, pol.id;
$$;

comment on function public.purchase_order_line_balances(uuid, uuid) is
    'Per-line ordered/received/allocated/remaining quantity and amount for one PO. Received comes from confirmed, non-voided receipts.';

-- ---------------------------------------------------------------------------
-- 5. Access
-- ---------------------------------------------------------------------------

alter table public.document_match_allocations enable row level security;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'document_match_allocations'
          and policyname = 'document_match_allocations_org_member'
    ) then
        create policy document_match_allocations_org_member
            on public.document_match_allocations
            for all to authenticated
            using (exists (
                select 1 from public.org_members m
                where m.org_id = document_match_allocations.org_id
                  and m.user_id = auth.uid()
                  and m.is_active = true
            ))
            with check (exists (
                select 1 from public.org_members m
                where m.org_id = document_match_allocations.org_id
                  and m.user_id = auth.uid()
                  and m.is_active = true
            ));
    end if;
end $$;

revoke all on function public.purchase_order_line_balances(uuid, uuid) from public, anon, authenticated;
grant execute on function public.purchase_order_line_balances(uuid, uuid) to service_role;
