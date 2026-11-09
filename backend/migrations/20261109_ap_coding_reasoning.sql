alter table if exists public.invoice_codings
    add column if not exists reasoning text;
