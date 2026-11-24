-- Ticket 10: resumable business onboarding.
--
-- One draft per user. Answers are written after every step so the wizard
-- can be left and resumed on the same step. The first workspace is created
-- only at the completion step; the draft keeps the resulting workspace id
-- so completion is idempotent.

create table if not exists public.onboarding_drafts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references auth.users(id) on delete cascade,
    step integer not null default 1 check (step between 1 and 6),
    completed boolean not null default false,
    data jsonb not null default '{}'::jsonb,
    workspace_id uuid references public.organizations(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_onboarding_drafts_user
    on public.onboarding_drafts (user_id);

alter table public.onboarding_drafts enable row level security;

drop policy if exists onboarding_drafts_owner on public.onboarding_drafts;
create policy onboarding_drafts_owner on public.onboarding_drafts
    for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
