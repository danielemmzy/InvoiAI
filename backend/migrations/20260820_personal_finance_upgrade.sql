-- InvoiAI Personal Finance Upgrade: accounts, transactions, net worth, alerts and bank-connection-ready model.
-- Run once in Supabase SQL Editor. All statements are idempotent.
create extension if not exists pgcrypto;

do $$ begin create type public.financial_account_type as enum ('checking','savings','cash','credit_card','investment','retirement','loan','other'); exception when duplicate_object then null; end $$;
do $$ begin create type public.transaction_type as enum ('income','expense','transfer','adjustment'); exception when duplicate_object then null; end $$;
do $$ begin create type public.alert_type as enum ('low_balance','budget_threshold','large_transaction','recurring_due','unusual_spend'); exception when duplicate_object then null; end $$;

create table if not exists public.financial_accounts (
 id uuid primary key default gen_random_uuid(), owner_type public.finance_owner_type not null, owner_id uuid not null,
 name text not null, account_type public.financial_account_type not null, institution_name text,
 mask text, currency text not null default 'USD', current_balance numeric(18,2) not null default 0,
 available_balance numeric(18,2), is_active boolean not null default true, is_manual boolean not null default true,
 provider text, provider_account_id text, last_synced_at timestamptz, metadata jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create unique index if not exists uq_financial_account_provider on public.financial_accounts(owner_type,owner_id,provider,provider_account_id) where provider is not null and provider_account_id is not null;
create index if not exists idx_financial_accounts_owner on public.financial_accounts(owner_type,owner_id,is_active);

create table if not exists public.financial_transactions (
 id uuid primary key default gen_random_uuid(), owner_type public.finance_owner_type not null, owner_id uuid not null,
 account_id uuid references public.financial_accounts(id) on delete set null, transaction_type public.transaction_type not null,
 amount numeric(18,2) not null check (amount >= 0), currency text not null default 'USD', merchant text,
 description text, category public.expense_category, transaction_date date not null, pending boolean not null default false,
 external_id text, metadata jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create unique index if not exists uq_financial_tx_external on public.financial_transactions(owner_type,owner_id,external_id) where external_id is not null;
create index if not exists idx_financial_tx_owner_date on public.financial_transactions(owner_type,owner_id,transaction_date desc);
create index if not exists idx_financial_tx_account_date on public.financial_transactions(account_id,transaction_date desc);

create table if not exists public.financial_alerts (
 id uuid primary key default gen_random_uuid(), owner_type public.finance_owner_type not null, owner_id uuid not null,
 alert_type public.alert_type not null, title text not null, message text not null, severity public.insight_severity not null default 'info',
 is_read boolean not null default false, is_dismissed boolean not null default false, data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(), expires_at timestamptz
);
create index if not exists idx_financial_alerts_owner on public.financial_alerts(owner_type,owner_id,is_dismissed,created_at desc);

create table if not exists public.net_worth_snapshots (
 id uuid primary key default gen_random_uuid(), owner_type public.finance_owner_type not null, owner_id uuid not null,
 snapshot_date date not null, assets numeric(18,2) not null default 0, liabilities numeric(18,2) not null default 0,
 net_worth numeric(18,2) generated always as (assets-liabilities) stored, created_at timestamptz not null default now(),
 unique(owner_type,owner_id,snapshot_date)
);
create index if not exists idx_net_worth_owner_date on public.net_worth_snapshots(owner_type,owner_id,snapshot_date desc);

-- RLS: backend service role is used by FastAPI; direct client access is denied unless explicitly granted later.
alter table public.financial_accounts enable row level security;
alter table public.financial_transactions enable row level security;
alter table public.financial_alerts enable row level security;
alter table public.net_worth_snapshots enable row level security;

-- No public/anon policies are created intentionally. Backend authorization remains the data boundary.
