-- Payment lifecycle: tenant isolation, idempotency, event history and returned state.
-- Safe to re-run. Provider credentials and bank account/routing values are never stored here.

create table if not exists public.payment_instructions (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete restrict,
  vendor_id uuid references public.vendors(id) on delete restrict,
  amount numeric(18,2) not null check (amount > 0),
  currency char(3) not null default 'USD',
  payment_method text,
  scheduled_date date,
  requested_by uuid,
  approved_by uuid,
  authorized_by uuid,
  approval_workflow_id uuid,
  provider text,
  provider_payment_id text,
  idempotency_key text not null,
  status text not null default 'requested',
  failure_reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, idempotency_key)
);

alter table public.payment_instructions add column if not exists payment_method text;
alter table public.payment_instructions add column if not exists scheduled_date date;
alter table public.payment_instructions add column if not exists requested_by uuid;
alter table public.payment_instructions add column if not exists approved_by uuid;
alter table public.payment_instructions add column if not exists authorized_by uuid;
alter table public.payment_instructions add column if not exists approval_workflow_id uuid;
alter table public.payment_instructions add column if not exists provider text;
alter table public.payment_instructions add column if not exists provider_payment_id text;
alter table public.payment_instructions add column if not exists idempotency_key text;
alter table public.payment_instructions add column if not exists failure_reason text;
alter table public.payment_instructions add column if not exists metadata jsonb not null default '{}'::jsonb;
alter table public.payment_instructions add column if not exists created_at timestamptz not null default now();
alter table public.payment_instructions add column if not exists updated_at timestamptz not null default now();

create unique index if not exists uq_payment_instruction_idempotency on public.payment_instructions(org_id,idempotency_key) where idempotency_key is not null;
create unique index if not exists uq_payment_instruction_provider_ref on public.payment_instructions(org_id,provider,provider_payment_id) where provider_payment_id is not null;
create index if not exists idx_payment_instruction_document on public.payment_instructions(org_id,document_id,created_at desc);
create index if not exists idx_payment_instruction_due on public.payment_instructions(status,scheduled_date) where status = 'scheduled';

create table if not exists public.payment_instruction_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  payment_instruction_id uuid not null references public.payment_instructions(id) on delete cascade,
  from_status text,
  to_status text not null,
  actor_id uuid,
  reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_payment_instruction_events_history on public.payment_instruction_events(org_id,payment_instruction_id,created_at);

alter table public.payment_instructions enable row level security;
alter table public.payment_instruction_events enable row level security;
revoke all on public.payment_instructions, public.payment_instruction_events from anon;
revoke all on public.payment_instructions, public.payment_instruction_events from authenticated;
grant select, insert, update, delete on public.payment_instructions to authenticated;
grant select on public.payment_instruction_events to authenticated;

drop policy if exists payment_instructions_org_member on public.payment_instructions;
create policy payment_instructions_org_member on public.payment_instructions for all to authenticated
using (exists(select 1 from public.org_members m where m.org_id=payment_instructions.org_id and m.user_id=auth.uid() and m.is_active=true))
with check (exists(select 1 from public.org_members m where m.org_id=payment_instructions.org_id and m.user_id=auth.uid() and m.is_active=true));
drop policy if exists payment_instruction_events_org_member on public.payment_instruction_events;
create policy payment_instruction_events_org_member on public.payment_instruction_events for select to authenticated
using (exists(select 1 from public.org_members m where m.org_id=payment_instruction_events.org_id and m.user_id=auth.uid() and m.is_active=true));

comment on table public.payment_instruction_events is 'Append-only audit trail for payment instruction lifecycle transitions.';
comment on column public.payment_instructions.provider_payment_id is 'External provider reference only; never store bank account or routing credentials.';

-- Keep the status write and append-only audit event in the same database transaction.
create or replace function public.transition_payment_instruction_with_event(
  p_org_id uuid,
  p_instruction_id uuid,
  p_expected_status text,
  p_to_status text,
  p_actor_id uuid default null,
  p_reason text default null,
  p_extra_fields jsonb default '{}'::jsonb
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.payment_instructions%rowtype;
begin
  update public.payment_instructions
     set status = p_to_status,
         updated_at = now(),
         provider = case when p_extra_fields ? 'provider' then p_extra_fields->>'provider' else provider end,
         provider_payment_id = case when p_extra_fields ? 'provider_payment_id' then p_extra_fields->>'provider_payment_id' else provider_payment_id end,
         failure_reason = case when p_extra_fields ? 'failure_reason' then p_extra_fields->>'failure_reason' else failure_reason end,
         approval_workflow_id = case when p_extra_fields ? 'approval_workflow_id' then nullif(p_extra_fields->>'approval_workflow_id','')::uuid else approval_workflow_id end,
         approved_by = case when p_extra_fields ? 'approved_by' then nullif(p_extra_fields->>'approved_by','')::uuid else approved_by end,
         authorized_by = case when p_extra_fields ? 'authorized_by' then nullif(p_extra_fields->>'authorized_by','')::uuid else authorized_by end,
         metadata = case when p_extra_fields ? 'metadata' and jsonb_typeof(p_extra_fields->'metadata') = 'object' then metadata || (p_extra_fields->'metadata') else metadata end
   where org_id = p_org_id and id = p_instruction_id and status = p_expected_status
   returning * into v_row;

  if not found then
    return null;
  end if;

  insert into public.payment_instruction_events(
    org_id, payment_instruction_id, from_status, to_status, actor_id, reason, metadata
  ) values (
    p_org_id, p_instruction_id, p_expected_status, p_to_status, p_actor_id, p_reason,
    coalesce(p_extra_fields, '{}'::jsonb)
  );

  return to_jsonb(v_row);
end;
$$;

revoke all on function public.transition_payment_instruction_with_event(uuid,uuid,text,text,uuid,text,jsonb) from public, anon, authenticated;
grant execute on function public.transition_payment_instruction_with_event(uuid,uuid,text,text,uuid,text,jsonb) to service_role;
