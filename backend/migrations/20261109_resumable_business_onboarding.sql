-- Ticket 10: resumable onboarding and retained business profile.
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
create index if not exists idx_onboarding_drafts_user on public.onboarding_drafts(user_id);
alter table public.onboarding_drafts enable row level security;
drop policy if exists onboarding_drafts_owner on public.onboarding_drafts;
create policy onboarding_drafts_owner on public.onboarding_drafts
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

alter table public.organizations
    add column if not exists business_type text,
    add column if not exists monthly_invoice_volume text,
    add column if not exists accounting_software text;

-- Atomically reserve one workspace ID per user before the multi-repository
-- bootstrap begins. Retrying completion reuses that ID and cannot create a
-- second workspace. Bootstrap itself remains a compensating workflow.
create or replace function public.claim_onboarding_workspace(p_user_id uuid)
returns uuid language sql security definer set search_path = public as $$
    update onboarding_drafts
       set workspace_id = coalesce(workspace_id, gen_random_uuid()), updated_at = now()
     where user_id = p_user_id and completed = false
     returning workspace_id;
$$;
revoke all on function public.claim_onboarding_workspace(uuid) from public, anon, authenticated;
grant execute on function public.claim_onboarding_workspace(uuid) to service_role;
