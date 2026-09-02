-- Stripe webhook idempotency and durable processing state.
-- Safe to run after the existing subscriptions/organizations schema.

create table if not exists public.stripe_events (
    id uuid primary key default gen_random_uuid(),
    stripe_event_id text not null unique,
    event_type text not null,
    status text not null default 'processing',
    payload jsonb not null default '{}'::jsonb,
    attempts integer not null default 1,
    last_error text,
    processing_started_at timestamptz,
    processed_at timestamptz,
    failed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint stripe_events_status_check check (status in ('processing','processed','failed')),
    constraint stripe_events_attempts_check check (attempts >= 0)
);

alter table public.stripe_events add column if not exists stripe_event_id text;
alter table public.stripe_events add column if not exists event_type text;
alter table public.stripe_events add column if not exists status text default 'processing';
alter table public.stripe_events add column if not exists payload jsonb default '{}'::jsonb;
alter table public.stripe_events add column if not exists attempts integer default 1;
alter table public.stripe_events add column if not exists last_error text;
alter table public.stripe_events add column if not exists processing_started_at timestamptz;
alter table public.stripe_events add column if not exists processed_at timestamptz;
alter table public.stripe_events add column if not exists failed_at timestamptz;
alter table public.stripe_events add column if not exists created_at timestamptz default now();
alter table public.stripe_events add column if not exists updated_at timestamptz default now();

create unique index if not exists ux_stripe_events_event_id
    on public.stripe_events (stripe_event_id);
create index if not exists ix_stripe_events_status_created
    on public.stripe_events (status, created_at);
create index if not exists ix_stripe_events_processing_started
    on public.stripe_events (status, processing_started_at);
