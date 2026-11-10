-- The table was referenced by the application before it was represented in
-- the checked-in migration chain. Create its minimum known contract for fresh
-- installs; IF NOT EXISTS preserves deployments that already created it.
create table if not exists public.ap_email_intake_addresses (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references public.organizations(id) on delete cascade,
    email_address text not null,
    is_active boolean not null default true,
    created_by uuid,
    created_at timestamptz not null default now()
);

alter table public.ap_email_intake_addresses enable row level security;
revoke all on public.ap_email_intake_addresses from public, anon, authenticated;
grant select, insert, update, delete on public.ap_email_intake_addresses to service_role;

-- Refuse to guess which legacy active address should survive existing violations.
do $$
begin
    if exists (
        select 1
        from public.ap_email_intake_addresses
        where is_active is true
        group by org_id
        having count(*) > 1
    ) then
        raise exception 'Resolve multiple active AP email addresses per organization before applying address rotation.';
    end if;

    if exists (
        select 1
        from public.ap_email_intake_addresses
        where is_active is true
        group by lower(email_address)
        having count(*) > 1
    ) then
        raise exception 'Resolve duplicate active AP email addresses before applying address rotation.';
    end if;
end;
$$;

create unique index if not exists uq_ap_email_address_one_active_per_org
    on public.ap_email_intake_addresses(org_id)
    where is_active is true;

create unique index if not exists uq_ap_email_address_unique_active_value
    on public.ap_email_intake_addresses(lower(email_address))
    where is_active is true;

create or replace function public.manage_ap_email_intake_address(
    p_org_id uuid,
    p_created_by uuid,
    p_email_address text,
    p_rotate boolean default false
)
returns setof public.ap_email_intake_addresses
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    v_address public.ap_email_intake_addresses%rowtype;
begin
    if p_org_id is null or p_created_by is null then
        raise exception 'Organization and actor are required.';
    end if;
    if p_email_address is null or p_email_address !~ '^[^@[:space:]]+@[^@[:space:]]+$' then
        raise exception 'A valid forwarding address is required.';
    end if;

    perform pg_advisory_xact_lock(hashtextextended('ap_email_intake_addresses:' || p_org_id::text, 0));

    if not coalesce(p_rotate, false) then
        select * into v_address
        from public.ap_email_intake_addresses
        where org_id = p_org_id and is_active is true
        limit 1;

        if found then
            return next v_address;
            return;
        end if;
    else
        update public.ap_email_intake_addresses
        set is_active = false
        where org_id = p_org_id and is_active is true;
    end if;

    insert into public.ap_email_intake_addresses (org_id, email_address, is_active, created_by)
    values (p_org_id, lower(p_email_address), true, p_created_by)
    returning * into v_address;

    return next v_address;
end;
$$;

revoke all on function public.manage_ap_email_intake_address(uuid, uuid, text, boolean) from public, anon, authenticated;
grant execute on function public.manage_ap_email_intake_address(uuid, uuid, text, boolean) to service_role;
