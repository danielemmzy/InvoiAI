-- Keep invitation reservations and acceptance within the current plan's seat cap.
create or replace function public.create_org_member_invitation(
    p_org_id uuid,
    p_seat_limit integer,
    p_role text,
    p_department text,
    p_spending_limit numeric,
    p_invited_by uuid,
    p_invite_email text,
    p_invite_token text,
    p_expires_at timestamptz
) returns setof public.org_members
language plpgsql security definer set search_path = public as $$
declare
    active_count integer;
    pending_count integer;
begin
    perform pg_advisory_xact_lock(hashtext(p_org_id::text));

    select count(distinct user_id) into active_count
      from org_members where org_id = p_org_id and is_active = true and user_id is not null;
    select count(*) into pending_count
      from org_members
     where org_id = p_org_id and is_active = false
       and invite_token is not null and (invite_expires_at is null or invite_expires_at > now());

    if p_seat_limit is not null and active_count + pending_count >= p_seat_limit then
        raise exception 'SEAT_LIMIT_REACHED' using errcode = 'P0001';
    end if;
    if exists (
        select 1 from org_members
         where org_id = p_org_id and is_active = false
           and invite_token is not null and (invite_expires_at is null or invite_expires_at > now())
           and lower(invite_email) = lower(p_invite_email)
    ) then
        raise exception 'INVITATION_ALREADY_EXISTS' using errcode = 'P0001';
    end if;

    return query
    insert into org_members (
        org_id, role, department, spending_limit, invited_by,
        invite_email, invite_token, invite_expires_at, is_active
    ) values (
        p_org_id, p_role, p_department, p_spending_limit, p_invited_by,
        p_invite_email, p_invite_token, p_expires_at, false
    ) returning *;
end;
$$;

create or replace function public.accept_org_member_invitation(
    p_invite_token text,
    p_user_id uuid,
    p_seat_limit integer
) returns setof public.org_members
language plpgsql security definer set search_path = public as $$
declare
    invitation public.org_members%rowtype;
    target_org uuid;
    active_count integer;
    already_active boolean;
begin
    select org_id into target_org
      from org_members where invite_token = p_invite_token;
    if not found then raise exception 'INVITATION_NOT_FOUND' using errcode = 'P0002'; end if;

    perform pg_advisory_xact_lock(hashtext(target_org::text));
    select * into invitation from org_members
     where invite_token = p_invite_token for update;
    if not found then raise exception 'INVITATION_NOT_FOUND' using errcode = 'P0002'; end if;
    if invitation.invite_expires_at is not null and invitation.invite_expires_at < now() then
        raise exception 'INVITATION_EXPIRED' using errcode = 'P0001';
    end if;

    select count(distinct user_id) into active_count
      from org_members where org_id = invitation.org_id and is_active = true and user_id is not null;
    select exists (
        select 1 from org_members
         where org_id = invitation.org_id and user_id = p_user_id and is_active = true
    ) into already_active;
    if p_seat_limit is not null and not already_active and active_count >= p_seat_limit then
        raise exception 'SEAT_LIMIT_REACHED' using errcode = 'P0001';
    end if;

    return query
    update org_members
       set user_id = p_user_id, is_active = true, joined_at = now(),
           invite_email = null, invite_token = null, invite_expires_at = null,
           updated_at = now()
     where id = invitation.id returning *;
end;
$$;

create or replace function public.resend_org_member_invitation(
    p_membership_id uuid,
    p_seat_limit integer,
    p_invite_token text,
    p_expires_at timestamptz
) returns setof public.org_members
language plpgsql security definer set search_path = public as $$
declare
    member public.org_members%rowtype;
    target_org uuid;
    active_count integer;
    pending_count integer;
begin
    select org_id into target_org from org_members where id = p_membership_id;
    if not found then
        raise exception 'PENDING_INVITATION_NOT_FOUND' using errcode = 'P0002';
    end if;
    perform pg_advisory_xact_lock(hashtext(target_org::text));
    select * into member from org_members where id = p_membership_id for update;
    if not found or member.is_active or member.invite_email is null then
        raise exception 'PENDING_INVITATION_NOT_FOUND' using errcode = 'P0002';
    end if;
    select count(distinct user_id) into active_count
      from org_members where org_id = member.org_id and is_active = true and user_id is not null;
    select count(*) into pending_count from org_members
     where org_id = member.org_id and is_active = false and id <> member.id
       and invite_token is not null and (invite_expires_at is null or invite_expires_at > now());
    if p_seat_limit is not null and active_count + pending_count >= p_seat_limit then
        raise exception 'SEAT_LIMIT_REACHED' using errcode = 'P0001';
    end if;
    return query
    update org_members
       set invite_token = p_invite_token, invite_expires_at = p_expires_at,
           updated_at = now()
     where id = member.id and is_active = false returning *;
end;
$$;

revoke all on function public.create_org_member_invitation(uuid, integer, text, text, numeric, uuid, text, text, timestamptz) from public, anon, authenticated;
revoke all on function public.accept_org_member_invitation(text, uuid, integer) from public, anon, authenticated;
revoke all on function public.resend_org_member_invitation(uuid, integer, text, timestamptz) from public, anon, authenticated;
grant execute on function public.create_org_member_invitation(uuid, integer, text, text, numeric, uuid, text, text, timestamptz) to service_role;
grant execute on function public.accept_org_member_invitation(text, uuid, integer) to service_role;
grant execute on function public.resend_org_member_invitation(uuid, integer, text, timestamptz) to service_role;
