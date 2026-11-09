-- Retry-safe inbound email processing. Safe to re-run.
alter table public.ap_email_intake_events add column if not exists error_message text;
alter table public.ap_email_intake_events add column if not exists processed_at timestamptz;
create unique index if not exists uq_ap_email_intake_message on public.ap_email_intake_events(intake_address_id, provider_message_id);
create table if not exists public.ap_email_intake_attachments (
 id uuid primary key default gen_random_uuid(), org_id uuid not null references public.organizations(id) on delete cascade,
 event_id uuid not null references public.ap_email_intake_events(id) on delete cascade, attachment_index integer not null check (attachment_index >= 0),
 filename text not null, content_sha256 text not null, idempotency_key text not null unique, status text not null default 'processing' check(status in ('processing','processed','failed')),
 document_id uuid references public.documents(id) on delete set null, error_message text, created_at timestamptz not null default now(), processed_at timestamptz,
 unique(event_id, attachment_index));
create index if not exists idx_ap_email_attachment_event on public.ap_email_intake_attachments(org_id,event_id);
alter table public.ap_email_intake_attachments enable row level security;
revoke all on public.ap_email_intake_attachments from anon, authenticated;
