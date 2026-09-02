-- V2 notification delivery infrastructure.
-- Run this migration in Supabase/PostgreSQL before enabling NotificationWorker.

create table if not exists public.notification_deliveries (
    id uuid primary key default gen_random_uuid(),
    notification_id uuid not null references public.notifications(id) on delete cascade,
    user_id uuid not null,
    organization_id uuid,
    channel text not null,
    provider text not null,
    status text not null default 'queued',
    idempotency_key text not null,
    recipient text,
    payload jsonb not null default '{}'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    attempt_count integer not null default 0,
    last_attempt_at timestamptz,
    last_error text,
    failed_at timestamptz,
    provider_message_id text,
    provider_error_code text,
    provider_response jsonb not null default '{}'::jsonb,
    next_retry_at timestamptz,
    queued_at timestamptz,
    processing_started_at timestamptz,
    sent_at timestamptz,
    delivered_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint notification_deliveries_channel_check
        check (channel in ('in_app','email','push','sms')),
    constraint notification_deliveries_status_check
        check (status in ('queued','processing','sent','delivered','failed','retrying','cancelled')),
    constraint notification_deliveries_attempt_count_check
        check (attempt_count >= 0)
);

alter table public.notification_deliveries add column if not exists idempotency_key text;
alter table public.notification_deliveries add column if not exists recipient text;
alter table public.notification_deliveries add column if not exists payload jsonb not null default '{}'::jsonb;
alter table public.notification_deliveries add column if not exists metadata jsonb not null default '{}'::jsonb;
alter table public.notification_deliveries add column if not exists attempt_count integer not null default 0;
alter table public.notification_deliveries add column if not exists last_attempt_at timestamptz;
alter table public.notification_deliveries add column if not exists last_error text;
alter table public.notification_deliveries add column if not exists failed_at timestamptz;
alter table public.notification_deliveries add column if not exists provider_error_code text;
alter table public.notification_deliveries add column if not exists provider_response jsonb not null default '{}'::jsonb;
alter table public.notification_deliveries add column if not exists queued_at timestamptz;
alter table public.notification_deliveries add column if not exists processing_started_at timestamptz;
alter table public.notification_deliveries add column if not exists delivered_at timestamptz;
alter table public.notification_deliveries add column if not exists updated_at timestamptz not null default now();

create unique index if not exists uq_notification_deliveries_idempotency_key
    on public.notification_deliveries (idempotency_key);

create index if not exists idx_notification_deliveries_queue
    on public.notification_deliveries (status, next_retry_at, created_at, id);

create index if not exists idx_notification_deliveries_processing
    on public.notification_deliveries (status, processing_started_at)
    where status = 'processing';

create index if not exists idx_notification_deliveries_notification
    on public.notification_deliveries (notification_id, created_at desc, id desc);

create index if not exists idx_notification_deliveries_user
    on public.notification_deliveries (user_id, created_at desc, id desc);

create index if not exists idx_notification_deliveries_provider_message
    on public.notification_deliveries (provider, provider_message_id)
    where provider_message_id is not null;

create or replace function public.claim_notification_deliveries(p_limit integer default 10)
returns setof public.notification_deliveries
language plpgsql
security definer
set search_path = public
as $$
declare
    claimed_ids uuid[];
begin
    with candidates as (
        select id
        from public.notification_deliveries
        where status in ('queued','retrying')
          and (next_retry_at is null or next_retry_at <= now())
        order by created_at asc, id asc
        for update skip locked
        limit greatest(p_limit, 0)
    ), claimed as (
        update public.notification_deliveries d
        set status = 'processing',
            processing_started_at = now(),
            last_attempt_at = now(),
            attempt_count = d.attempt_count + 1,
            updated_at = now()
        from candidates c
        where d.id = c.id
        returning d.id
    )
    select coalesce(array_agg(id), '{}'::uuid[]) into claimed_ids from claimed;

    return query
    select d.*
    from public.notification_deliveries d
    where d.id = any(claimed_ids)
    order by d.created_at asc, d.id asc;
end;
$$;

create or replace function public.recover_stale_notification_deliveries(
    p_timeout_seconds integer default 300,
    p_limit integer default 100
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    recovered integer;
begin
    with stale as (
        select id
        from public.notification_deliveries
        where status = 'processing'
          and processing_started_at < now() - make_interval(secs => greatest(p_timeout_seconds, 1))
        order by processing_started_at asc, id asc
        for update skip locked
        limit greatest(p_limit, 0)
    )
    update public.notification_deliveries d
    set status = 'retrying',
        next_retry_at = now(),
        last_error = 'Recovered stale processing delivery.',
        processing_started_at = null,
        updated_at = now()
    from stale s
    where d.id = s.id;

    get diagnostics recovered = row_count;
    return recovered;
end;
$$;

revoke all on function public.claim_notification_deliveries(integer) from public;
revoke all on function public.recover_stale_notification_deliveries(integer, integer) from public;
