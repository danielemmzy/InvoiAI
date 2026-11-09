alter table public.vendors
    add column if not exists is_active boolean not null default true,
    add column if not exists provider text,
    add column if not exists external_id text;

create unique index if not exists uq_vendors_org_provider_external
    on public.vendors (org_id, provider, external_id)
    where provider is not null and external_id is not null;

create index if not exists idx_vendors_org_active_name
    on public.vendors (org_id, is_active, normalized_name);
