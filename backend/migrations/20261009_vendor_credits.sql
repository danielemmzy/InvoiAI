-- Vendor credits are organization-scoped credit notes and allocations.
create table if not exists public.vendor_credits (
 id uuid primary key default gen_random_uuid(), org_id uuid not null references public.organizations(id) on delete cascade,
 vendor_id uuid not null references public.vendors(id) on delete restrict,
 credit_number text, reason text, amount numeric(18,2) not null check(amount > 0),
 remaining_amount numeric(18,2) not null check(remaining_amount >= 0 and remaining_amount <= amount),
 currency char(3) not null default 'USD', issued_at date not null default current_date, expires_at date,
 status text not null default 'open' check(status in ('open','partially_applied','applied','expired','cancelled')),
 notes text, created_by uuid, cancelled_at timestamptz, cancellation_reason text,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 check(expires_at is null or expires_at >= issued_at)
);
create unique index if not exists uq_vendor_credit_number on public.vendor_credits(org_id,vendor_id,credit_number) where credit_number is not null;
create index if not exists idx_vendor_credits_vendor on public.vendor_credits(org_id,vendor_id,created_at desc);
create table if not exists public.vendor_credit_applications (
 id uuid primary key default gen_random_uuid(), org_id uuid not null references public.organizations(id) on delete cascade,
 vendor_credit_id uuid not null references public.vendor_credits(id) on delete restrict,
 vendor_id uuid not null references public.vendors(id) on delete restrict,
 document_id uuid not null references public.documents(id) on delete restrict,
 amount numeric(18,2) not null check(amount > 0), currency char(3) not null,
 applied_by uuid, created_at timestamptz not null default now()
);
create index if not exists idx_vendor_credit_app_credit on public.vendor_credit_applications(org_id,vendor_credit_id,created_at desc);
create index if not exists idx_vendor_credit_app_document on public.vendor_credit_applications(org_id,document_id);
create table if not exists public.vendor_credit_events (
 id uuid primary key default gen_random_uuid(), org_id uuid not null references public.organizations(id) on delete cascade,
 vendor_credit_id uuid not null references public.vendor_credits(id) on delete cascade,
 actor_id uuid, event_type text not null, details jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);
create index if not exists idx_vendor_credit_events_credit on public.vendor_credit_events(org_id,vendor_credit_id,created_at desc);

alter table public.vendor_credits enable row level security;
alter table public.vendor_credit_applications enable row level security;
alter table public.vendor_credit_events enable row level security;
revoke all on public.vendor_credits,public.vendor_credit_applications,public.vendor_credit_events from anon;
revoke all on public.vendor_credits,public.vendor_credit_applications,public.vendor_credit_events from authenticated;
grant select,insert,update,delete on public.vendor_credits,public.vendor_credit_applications to authenticated;
grant select on public.vendor_credit_events to authenticated;
drop policy if exists vendor_credits_org_member on public.vendor_credits;
create policy vendor_credits_org_member on public.vendor_credits for all to authenticated using (exists(select 1 from public.org_members m where m.org_id=vendor_credits.org_id and m.user_id=auth.uid() and m.is_active=true)) with check (exists(select 1 from public.org_members m where m.org_id=vendor_credits.org_id and m.user_id=auth.uid() and m.is_active=true));
drop policy if exists vendor_credit_applications_org_member on public.vendor_credit_applications;
create policy vendor_credit_applications_org_member on public.vendor_credit_applications for all to authenticated using (exists(select 1 from public.org_members m where m.org_id=vendor_credit_applications.org_id and m.user_id=auth.uid() and m.is_active=true)) with check (exists(select 1 from public.org_members m where m.org_id=vendor_credit_applications.org_id and m.user_id=auth.uid() and m.is_active=true));
drop policy if exists vendor_credit_events_org_member on public.vendor_credit_events;
create policy vendor_credit_events_org_member on public.vendor_credit_events for select to authenticated using (exists(select 1 from public.org_members m where m.org_id=vendor_credit_events.org_id and m.user_id=auth.uid() and m.is_active=true));
