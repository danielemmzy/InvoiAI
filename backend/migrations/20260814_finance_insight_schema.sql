-- InvoiAI V2 finance + insight schema.
-- Idempotent Supabase migration. Safe to run after the initial V2 build.

DO $$
BEGIN
    CREATE TYPE public.expense_category AS ENUM (
        'housing','utilities','transport','food','subscriptions',
        'debt_payment','savings','healthcare','entertainment',
        'shopping','education','insurance','other'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE public.finance_owner_type AS ENUM ('organization','personal');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE public.goal_status AS ENUM ('active','achieved','abandoned');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE public.income_source AS ENUM (
        'salary','freelance','business','investment','gift','refund','other'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE public.insight_severity AS ENUM ('info','warning','critical');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE public.insight_type AS ENUM (
        'overdue','price_increase','anomaly','cashflow','duplicate'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE public.recurring_frequency AS ENUM (
        'weekly','biweekly','monthly','quarterly','annually'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS public.income_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type public.finance_owner_type NOT NULL,
    owner_id uuid NOT NULL,
    amount numeric(18,2) NOT NULL CHECK (amount >= 0),
    currency text NOT NULL DEFAULT 'USD',
    source public.income_source NOT NULL,
    description text,
    received_date date NOT NULL,
    is_recurring boolean NOT NULL DEFAULT false,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.expenses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type public.finance_owner_type NOT NULL,
    owner_id uuid NOT NULL,
    amount numeric(18,2) NOT NULL CHECK (amount >= 0),
    currency text NOT NULL DEFAULT 'USD',
    description text NOT NULL,
    category public.expense_category NOT NULL DEFAULT 'other',
    expense_date date NOT NULL,
    document_id uuid,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.budget_categories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type public.finance_owner_type NOT NULL,
    owner_id uuid NOT NULL,
    category public.expense_category NOT NULL,
    monthly_limit numeric(18,2) NOT NULL CHECK (monthly_limit >= 0),
    spent numeric(18,2) NOT NULL DEFAULT 0 CHECK (spent >= 0),
    period_month date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(owner_type, owner_id, category, period_month)
);

CREATE TABLE IF NOT EXISTS public.recurring_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type public.finance_owner_type NOT NULL,
    owner_id uuid NOT NULL,
    name text NOT NULL,
    amount numeric(18,2) NOT NULL CHECK (amount >= 0),
    frequency public.recurring_frequency NOT NULL,
    next_due_date date NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.debts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type public.finance_owner_type NOT NULL,
    owner_id uuid NOT NULL,
    name text NOT NULL,
    balance numeric(18,2) NOT NULL CHECK (balance >= 0),
    interest_rate numeric(9,4) NOT NULL DEFAULT 0 CHECK (interest_rate >= 0),
    minimum_payment numeric(18,2) NOT NULL DEFAULT 0 CHECK (minimum_payment >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.goals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type public.finance_owner_type NOT NULL,
    owner_id uuid NOT NULL,
    name text NOT NULL,
    target_amount numeric(18,2) NOT NULL CHECK (target_amount >= 0),
    current_amount numeric(18,2) NOT NULL DEFAULT 0 CHECK (current_amount >= 0),
    target_date date,
    status public.goal_status NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.allocation_plans (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type public.finance_owner_type NOT NULL,
    owner_id uuid NOT NULL,
    income numeric(18,2) NOT NULL CHECK (income >= 0),
    plan jsonb NOT NULL DEFAULT '{}'::jsonb,
    advice text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.insights (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    insight_type public.insight_type NOT NULL,
    severity public.insight_severity NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    affected_resource_type text,
    affected_resource_id uuid,
    recommended_action text,
    is_read boolean NOT NULL DEFAULT false,
    is_dismissed boolean NOT NULL DEFAULT false,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_income_owner_date
    ON public.income_entries(owner_type, owner_id, received_date DESC);
CREATE INDEX IF NOT EXISTS idx_expense_owner_date
    ON public.expenses(owner_type, owner_id, expense_date DESC);
CREATE INDEX IF NOT EXISTS idx_budget_owner_period
    ON public.budget_categories(owner_type, owner_id, period_month);
CREATE INDEX IF NOT EXISTS idx_recurring_owner_due
    ON public.recurring_items(owner_type, owner_id, next_due_date)
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_debt_owner
    ON public.debts(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_goal_owner_status
    ON public.goals(owner_type, owner_id, status);
CREATE INDEX IF NOT EXISTS idx_allocation_owner_created
    ON public.allocation_plans(owner_type, owner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_insights_org_active
    ON public.insights(org_id, is_dismissed, severity, created_at DESC);
