-- Ticket 7: six-digit email verification OTP challenges.
-- Additive and idempotent. This table is service-role only: it stores a hash
-- of each code, never the code itself, and no client policy is granted.
--
-- A row is single-use. Resending invalidates the previous pending row for the
-- same user. Attempts are counted server-side and the row is locked after the
-- configured maximum.

create table if not exists public.auth_email_verifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    email text not null,
    purpose text not null default 'email_verification',
    code_hash text not null,
    status text not null default 'pending'
        check (status in ('pending', 'verified', 'expired', 'locked')),
    attempts integer not null default 0,
    max_attempts integer not null default 5,
    resend_count integer not null default 0,
    last_sent_at timestamptz not null default now(),
    expires_at timestamptz not null,
    verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_auth_email_verifications_email_created
    on public.auth_email_verifications(lower(email), created_at desc);

create index if not exists idx_auth_email_verifications_user_created
    on public.auth_email_verifications(user_id, created_at desc);

create index if not exists idx_auth_email_verifications_user_status
    on public.auth_email_verifications(user_id, status);

alter table public.auth_email_verifications enable row level security;

comment on table public.auth_email_verifications is
    'Hashed, single-use six-digit email verification codes. Service-role access only; codes are never stored or logged in plaintext.';
