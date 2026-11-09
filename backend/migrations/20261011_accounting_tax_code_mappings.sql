-- Provider-specific tax mappings. Actual provider tax behavior must be sandbox-tested.
create table if not exists public.accounting_tax_code_mappings (
 id uuid primary key default gen_random_uuid(), org_id uuid not null references public.organizations(id) on delete cascade,
 provider text not null check(provider in ('quickbooks','xero')), source_tax_rate numeric(9,6) not null check(source_tax_rate >= 0 and source_tax_rate <= 100),
 source_tax_code text, external_tax_code_id text not null, external_tax_code_name text, is_active boolean not null default true,
 created_by uuid, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 unique(org_id,provider,source_tax_rate,source_tax_code));
create index if not exists idx_accounting_tax_mapping_lookup on public.accounting_tax_code_mappings(org_id,provider,source_tax_rate) where is_active=true;
alter table public.accounting_tax_code_mappings enable row level security;
revoke all on public.accounting_tax_code_mappings from anon;
drop policy if exists accounting_tax_mappings_org_member on public.accounting_tax_code_mappings;
create policy accounting_tax_mappings_org_member on public.accounting_tax_code_mappings for all to authenticated
using (exists(select 1 from public.org_members m where m.org_id=accounting_tax_code_mappings.org_id and m.user_id=auth.uid() and m.is_active=true))
with check (exists(select 1 from public.org_members m where m.org_id=accounting_tax_code_mappings.org_id and m.user_id=auth.uid() and m.is_active=true));
