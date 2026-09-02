-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- InvoiAI AP Automation Phase 1
-- Safe/idempotent migration for Supabase/PostgreSQL.
-- Run after 20260817_backend_authorization_hardening.sql.
-- Backend uses the service-role client; RLS is deny-by-default
-- for anon/authenticated and is defense-in-depth.
-- ============================================================

DO $$ BEGIN
    CREATE TYPE public.invoice_ap_status AS ENUM (
        'received','extracting','validating','matching','coding',
        'awaiting_approval','approved','syncing_to_erp','payment_ready',
        'paid','reconciled','match_exception','coding_exception','rejected','on_hold'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_exception_type AS ENUM (
        'price_mismatch','quantity_mismatch','missing_po','missing_receipt',
        'duplicate_invoice','unknown_vendor','bank_account_change','invalid_tax',
        'gl_coding_required','budget_exceeded','currency_mismatch','amount_exceeds_po',
        'vendor_blocked','compliance_violation'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_exception_status AS ENUM ('open','in_review','resolved','waived','escalated');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_match_status AS ENUM ('not_required','pending','matched','partial_match','exception');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_coding_source AS ENUM ('rule','historical','ai_suggested','manual');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_coding_status AS ENUM ('pending','auto_coded','needs_review','approved');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_goods_receipt_status AS ENUM ('draft','confirmed','partial','complete','cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_dimension_type AS ENUM ('department','cost_center','project','location','class','custom');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE public.ap_tolerance_scope AS ENUM ('org','vendor','department','document_type');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS public.chart_of_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    external_id text,
    external_parent_id text,
    account_code text NOT NULL,
    account_name text NOT NULL,
    account_type text NOT NULL,
    account_subtype text,
    parent_account_id uuid REFERENCES public.chart_of_accounts(id),
    is_active boolean NOT NULL DEFAULT true,
    is_postable boolean NOT NULL DEFAULT true,
    source text NOT NULL DEFAULT 'manual',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_coa_org_code UNIQUE (org_id, account_code)
);
DROP INDEX IF EXISTS public.uq_coa_org_external;
CREATE UNIQUE INDEX IF NOT EXISTS uq_coa_org_external ON public.chart_of_accounts(org_id, external_id);
ALTER TABLE public.chart_of_accounts
    ADD COLUMN IF NOT EXISTS external_parent_id text;
CREATE INDEX IF NOT EXISTS ix_coa_org_active ON public.chart_of_accounts(org_id, is_active);
CREATE INDEX IF NOT EXISTS ix_coa_org_external_parent ON public.chart_of_accounts(org_id, external_parent_id);

CREATE OR REPLACE FUNCTION public.resolve_quickbooks_coa_parents(p_org_id uuid)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE updated_count integer;
BEGIN
    UPDATE public.chart_of_accounts child
       SET parent_account_id = parent.id, updated_at = now()
      FROM public.chart_of_accounts parent
     WHERE child.org_id = p_org_id
       AND parent.org_id = p_org_id
       AND child.source = 'quickbooks'
       AND child.external_parent_id IS NOT NULL
       AND parent.external_id = child.external_parent_id;
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END $$;
REVOKE ALL ON FUNCTION public.resolve_quickbooks_coa_parents(uuid) FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS public.accounting_dimensions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    dimension_type public.ap_dimension_type NOT NULL,
    external_id text,
    code text NOT NULL,
    name text NOT NULL,
    parent_id uuid REFERENCES public.accounting_dimensions(id),
    is_active boolean NOT NULL DEFAULT true,
    source text NOT NULL DEFAULT 'manual',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_dim_org_type_code UNIQUE (org_id, dimension_type, code)
);
CREATE INDEX IF NOT EXISTS ix_dim_org_type ON public.accounting_dimensions(org_id, dimension_type);

CREATE TABLE IF NOT EXISTS public.tax_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    external_id text,
    code text NOT NULL,
    name text NOT NULL,
    rate numeric(7,4) NOT NULL DEFAULT 0,
    jurisdiction text,
    is_active boolean NOT NULL DEFAULT true,
    source text NOT NULL DEFAULT 'manual',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_tax_org_code UNIQUE (org_id, code)
);
CREATE INDEX IF NOT EXISTS ix_tax_org_active ON public.tax_codes(org_id, is_active);

CREATE TABLE IF NOT EXISTS public.coding_rules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    vendor_id uuid,
    description_pattern text,
    sku_pattern text,
    gl_account_id uuid REFERENCES public.chart_of_accounts(id),
    department_id uuid REFERENCES public.accounting_dimensions(id),
    cost_center_id uuid REFERENCES public.accounting_dimensions(id),
    project_id uuid REFERENCES public.accounting_dimensions(id),
    tax_code_id uuid REFERENCES public.tax_codes(id),
    priority integer NOT NULL DEFAULT 100,
    is_active boolean NOT NULL DEFAULT true,
    match_count integer NOT NULL DEFAULT 0,
    created_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_rules_org_active ON public.coding_rules(org_id, is_active, priority);
CREATE INDEX IF NOT EXISTS ix_rules_vendor ON public.coding_rules(org_id, vendor_id);

CREATE TABLE IF NOT EXISTS public.invoice_codings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    document_id uuid NOT NULL,
    line_item_id uuid,
    gl_account_id uuid REFERENCES public.chart_of_accounts(id),
    department_id uuid REFERENCES public.accounting_dimensions(id),
    cost_center_id uuid REFERENCES public.accounting_dimensions(id),
    project_id uuid REFERENCES public.accounting_dimensions(id),
    location_id uuid REFERENCES public.accounting_dimensions(id),
    class_id uuid REFERENCES public.accounting_dimensions(id),
    tax_code_id uuid REFERENCES public.tax_codes(id),
    amount numeric(18,2),
    confidence numeric(5,2) NOT NULL DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 100),
    source public.ap_coding_source NOT NULL DEFAULT 'manual',
    coding_rule_id uuid REFERENCES public.coding_rules(id),
    status public.ap_coding_status NOT NULL DEFAULT 'pending',
    created_by uuid,
    approved_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_coding_line ON public.invoice_codings(document_id, COALESCE(line_item_id, '00000000-0000-0000-0000-000000000000'::uuid));
CREATE INDEX IF NOT EXISTS ix_invoice_codings_org_status ON public.invoice_codings(org_id, status);

CREATE TABLE IF NOT EXISTS public.goods_receipts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    purchase_order_id uuid,
    vendor_id uuid,
    receipt_number text,
    received_at timestamptz NOT NULL DEFAULT now(),
    received_by uuid,
    location_id uuid REFERENCES public.accounting_dimensions(id),
    status public.ap_goods_receipt_status NOT NULL DEFAULT 'draft',
    source text NOT NULL DEFAULT 'manual',
    external_id text,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_goods_receipts_org_po ON public.goods_receipts(org_id, purchase_order_id);

CREATE TABLE IF NOT EXISTS public.goods_receipt_lines (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    goods_receipt_id uuid NOT NULL REFERENCES public.goods_receipts(id) ON DELETE CASCADE,
    purchase_order_line_id uuid,
    description text,
    sku text,
    quantity_ordered numeric(18,4),
    quantity_received numeric(18,4) NOT NULL,
    quantity_accepted numeric(18,4),
    quantity_rejected numeric(18,4) NOT NULL DEFAULT 0,
    unit_of_measure text,
    unit_price numeric(18,4),
    warehouse_location text,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_goods_receipt_lines_receipt ON public.goods_receipt_lines(goods_receipt_id);

CREATE TABLE IF NOT EXISTS public.matching_tolerances (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    scope public.ap_tolerance_scope NOT NULL DEFAULT 'org',
    vendor_id uuid,
    department_id uuid,
    document_type text,
    quantity_percent numeric(5,2) NOT NULL DEFAULT 5.0,
    price_percent numeric(5,2) NOT NULL DEFAULT 2.0,
    amount_absolute numeric(18,2) NOT NULL DEFAULT 50.0,
    currency text NOT NULL DEFAULT 'USD',
    auto_approve_within_tol boolean NOT NULL DEFAULT false,
    match_mode text NOT NULL DEFAULT 'auto', -- auto, two_way, three_way
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.matching_tolerances ADD COLUMN IF NOT EXISTS match_mode text NOT NULL DEFAULT 'auto';
ALTER TABLE public.matching_tolerances DROP CONSTRAINT IF EXISTS chk_matching_tolerance_mode;
ALTER TABLE public.matching_tolerances ADD CONSTRAINT chk_matching_tolerance_mode CHECK (match_mode IN ('auto','two_way','three_way'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_matching_tolerance_scope ON public.matching_tolerances(org_id, scope, COALESCE(vendor_id, '00000000-0000-0000-0000-000000000000'::uuid), COALESCE(department_id, '00000000-0000-0000-0000-000000000000'::uuid), COALESCE(document_type, ''));

CREATE TABLE IF NOT EXISTS public.invoice_exceptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    document_id uuid NOT NULL,
    exception_type public.ap_exception_type NOT NULL,
    status public.ap_exception_status NOT NULL DEFAULT 'open',
    severity text NOT NULL DEFAULT 'warning',
    title text NOT NULL,
    description text,
    details jsonb NOT NULL DEFAULT '{}',
    expected_value text,
    actual_value text,
    variance text,
    resolution_note text,
    resolved_by uuid,
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_invoice_exceptions_org_status ON public.invoice_exceptions(org_id, status);
CREATE INDEX IF NOT EXISTS ix_invoice_exceptions_document ON public.invoice_exceptions(document_id);

CREATE TABLE IF NOT EXISTS public.invoice_status_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    document_id uuid NOT NULL,
    from_status public.invoice_ap_status,
    to_status public.invoice_ap_status NOT NULL,
    triggered_by text,
    actor_id uuid,
    reason text,
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_invoice_status_log_document ON public.invoice_status_log(document_id, created_at DESC);

-- Email intake: a tenant-specific forwarding address and an idempotency ledger.
CREATE TABLE IF NOT EXISTS public.ap_email_intake_addresses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    email_address text NOT NULL UNIQUE,
    is_active boolean NOT NULL DEFAULT true,
    created_by uuid,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ap_email_addresses_org ON public.ap_email_intake_addresses(org_id, is_active);

CREATE TABLE IF NOT EXISTS public.ap_email_intake_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    intake_address_id uuid NOT NULL REFERENCES public.ap_email_intake_addresses(id) ON DELETE CASCADE,
    provider_message_id text NOT NULL,
    sender_email text,
    subject text,
    attachment_count integer NOT NULL DEFAULT 0,
    processed boolean NOT NULL DEFAULT false,
    error_message text,
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz,
    CONSTRAINT uq_ap_email_provider_message UNIQUE (intake_address_id, provider_message_id)
);

-- Existing tables: AP state and coding projections.
ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS ap_status public.invoice_ap_status DEFAULT 'received',
    ADD COLUMN IF NOT EXISTS match_status public.ap_match_status DEFAULT 'not_required',
    ADD COLUMN IF NOT EXISTS two_way_match_passed boolean,
    ADD COLUMN IF NOT EXISTS three_way_match_passed boolean,
    ADD COLUMN IF NOT EXISTS match_exception_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gl_coding_status public.ap_coding_status DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS erp_bill_id text,
    ADD COLUMN IF NOT EXISTS erp_synced_at timestamptz,
    ADD COLUMN IF NOT EXISTS payment_ready_at timestamptz,
    ADD COLUMN IF NOT EXISTS goods_receipt_id uuid;

ALTER TABLE public.document_line_items
    ADD COLUMN IF NOT EXISTS gl_account_id uuid REFERENCES public.chart_of_accounts(id),
    ADD COLUMN IF NOT EXISTS gl_account_code text,
    ADD COLUMN IF NOT EXISTS gl_account_name text,
    ADD COLUMN IF NOT EXISTS department_id uuid REFERENCES public.accounting_dimensions(id),
    ADD COLUMN IF NOT EXISTS cost_center_id uuid REFERENCES public.accounting_dimensions(id),
    ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES public.accounting_dimensions(id),
    ADD COLUMN IF NOT EXISTS tax_code_id uuid REFERENCES public.tax_codes(id),
    ADD COLUMN IF NOT EXISTS coding_confidence numeric(5,2),
    ADD COLUMN IF NOT EXISTS coding_source public.ap_coding_source;

ALTER TABLE public.purchase_orders
    ADD COLUMN IF NOT EXISTS balance_remaining numeric(18,2),
    ADD COLUMN IF NOT EXISTS quantity_ordered numeric(18,4),
    ADD COLUMN IF NOT EXISTS quantity_received numeric(18,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quantity_invoiced numeric(18,4) NOT NULL DEFAULT 0;

ALTER TABLE public.vendors
    ADD COLUMN IF NOT EXISTS bank_change_pending boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS bank_change_requested_at timestamptz,
    ADD COLUMN IF NOT EXISTS bank_change_verified_at timestamptz;

CREATE INDEX IF NOT EXISTS ix_documents_ap_status ON public.documents(org_id, ap_status);
CREATE INDEX IF NOT EXISTS ix_documents_match_status ON public.documents(org_id, match_status);
CREATE INDEX IF NOT EXISTS ix_documents_erp_bill ON public.documents(org_id, erp_bill_id);

-- RPC used by the coding repository; service-role only in practice.
CREATE OR REPLACE FUNCTION public.increment_coding_rule_match(rule_id uuid)
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
    UPDATE public.coding_rules SET match_count = match_count + 1, updated_at = now() WHERE id = rule_id;
$$;
REVOKE ALL ON FUNCTION public.increment_coding_rule_match(uuid) FROM PUBLIC, anon, authenticated;

-- RLS: backend is the persistence boundary. No direct PostgREST access.
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'chart_of_accounts','accounting_dimensions','tax_codes','coding_rules','invoice_codings',
        'goods_receipts','goods_receipt_lines','matching_tolerances','invoice_exceptions',
        'invoice_status_log','ap_email_intake_addresses','ap_email_intake_events'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', t);
    END LOOP;
END $$;

-- No permissive policies are intentionally created. The service-role client bypasses RLS.
-- This prevents accidental direct frontend access to AP/accounting tables.
