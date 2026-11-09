-- Supports the per-organization inbound message window check.
create index if not exists idx_ap_email_intake_events_org_created
    on public.ap_email_intake_events(org_id, created_at desc);
create index if not exists idx_ap_email_intake_events_org_sender_created
    on public.ap_email_intake_events(org_id, sender_email, created_at desc);
