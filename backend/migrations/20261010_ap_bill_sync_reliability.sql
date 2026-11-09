-- Bill-sync lease and idempotency metadata. Safe to re-run.
alter table public.documents add column if not exists erp_sync_started_at timestamptz;
alter table public.documents add column if not exists erp_sync_error text;
alter table public.documents add column if not exists erp_sync_attempts integer not null default 0;
create index if not exists idx_documents_bill_sync_queue on public.documents(org_id, ap_status, erp_sync_started_at) where ap_enabled = true and document_type = 'invoice';
