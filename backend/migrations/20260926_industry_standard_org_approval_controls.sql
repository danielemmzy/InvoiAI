-- InvoiAI industry-standard organization access + approval controls.
-- Additive migration. Existing role/permission behavior remains compatible.

CREATE TABLE IF NOT EXISTS public.organization_roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    role_key text NOT NULL,
    name text NOT NULL,
    description text,
    permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
    is_system boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(org_id, role_key)
);

ALTER TABLE public.org_members
    ADD COLUMN IF NOT EXISTS access_role_id uuid REFERENCES public.organization_roles(id) ON DELETE SET NULL;

ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS ap_processed_by uuid REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_org_members_access_role ON public.org_members(access_role_id);

CREATE TABLE IF NOT EXISTS public.approval_authorities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    membership_id uuid NOT NULL REFERENCES public.org_members(id) ON DELETE CASCADE,
    approval_type text NOT NULL CHECK (approval_type IN ('invoice','payment')),
    currency text NOT NULL,
    limit_amount numeric(18,2) NOT NULL CHECK (limit_amount >= 0),
    can_self_approve boolean NOT NULL DEFAULT false,
    can_approve_exceptions boolean NOT NULL DEFAULT false,
    effective_from timestamptz,
    effective_until timestamptz,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(membership_id, approval_type, currency)
);

CREATE INDEX IF NOT EXISTS idx_approval_authorities_org_type
    ON public.approval_authorities(org_id, approval_type, is_active);

CREATE TABLE IF NOT EXISTS public.approval_delegations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    delegator_membership_id uuid NOT NULL REFERENCES public.org_members(id) ON DELETE CASCADE,
    delegatee_membership_id uuid NOT NULL REFERENCES public.org_members(id) ON DELETE CASCADE,
    scope jsonb NOT NULL DEFAULT '{"invoice":true,"payment":false}'::jsonb,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    reason text,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    CHECK (delegator_membership_id <> delegatee_membership_id),
    CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_approval_delegations_active
    ON public.approval_delegations(org_id, starts_at, ends_at)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS public.sod_rules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    rule_key text NOT NULL,
    name text NOT NULL,
    description text,
    enabled boolean NOT NULL DEFAULT true,
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(org_id, rule_key)
);

INSERT INTO public.sod_rules(org_id, rule_key, name, description, enabled, config)
SELECT o.id, v.rule_key, v.name, v.description, true, v.config
FROM public.organizations o
CROSS JOIN (VALUES
    ('no_self_approval','No self approval','The requester cannot approve their own invoice.', '{"applies_to":"invoice"}'::jsonb),
    ('processor_cannot_approve','Processor cannot approve','The member who processed an invoice cannot approve it.', '{"applies_to":"invoice"}'::jsonb),
    ('separate_payment_authorizer','Separate payment authorization','Invoice approval and payment authorization should be performed by different members.', '{"applies_to":"payment"}'::jsonb)
) AS v(rule_key,name,description,config)
ON CONFLICT (org_id, rule_key) DO NOTHING;

INSERT INTO public.organization_roles(org_id, role_key, name, description, permissions, is_system)
SELECT o.id, r.role_key, r.name, r.description, r.permissions::jsonb, true
FROM public.organizations o
CROSS JOIN (VALUES
    ('owner','Owner','Full organization ownership','["*"]'),
    ('admin','Admin','Organization administration','["organization:view","members:view","members:invite","members:remove","roles:manage","settings:view","settings:update","integrations:view","integrations:manage","audit:view"]'),
    ('finance_manager','Finance Manager','Finance oversight and invoice approval','["documents:view","documents:upload","documents:edit","vendors:view","vendors:manage","finance:view","finance:manage","ap:view","ap:process","ap:approve","payments:view","payments:approve"]'),
    ('ap_manager','AP Manager','Accounts payable operations and approval','["documents:view","documents:upload","documents:edit","vendors:view","ap:view","ap:process","ap:edit","ap:approve","ap:reject","ap_rules:manage"]'),
    ('ap_member','AP Member','Accounts payable processing','["documents:view","documents:upload","documents:edit","ap:view","ap:process","ap:edit","vendors:view"]'),
    ('payment_approver','Payment Approver','Payment authorization','["finance:view","payments:view","payments:approve","payments:authorize"]'),
    ('viewer','Viewer','Read-only access','["documents:view","vendors:view","finance:view","ap:view","payments:view"]')
) AS r(role_key,name,description,permissions)
ON CONFLICT (org_id, role_key) DO NOTHING;

INSERT INTO public.approval_authorities(org_id, membership_id, approval_type, currency, limit_amount, can_self_approve, can_approve_exceptions)
SELECT m.org_id, m.id, 'invoice', upper(coalesce(o.currency, 'USD')), m.spending_limit, false, true
FROM public.org_members m
JOIN public.organizations o ON o.id = m.org_id
WHERE m.spending_limit IS NOT NULL
ON CONFLICT (membership_id, approval_type, currency) DO NOTHING;

INSERT INTO public.approval_authorities(org_id, membership_id, approval_type, currency, limit_amount, can_self_approve, can_approve_exceptions)
SELECT m.org_id, m.id, 'payment', upper(coalesce(o.currency, 'USD')), m.payment_approval_limit, false, false
FROM public.org_members m
JOIN public.organizations o ON o.id = m.org_id
WHERE m.payment_approval_limit IS NOT NULL
ON CONFLICT (membership_id, approval_type, currency) DO NOTHING;

UPDATE public.org_members m
SET access_role_id = r.id
FROM public.organization_roles r
WHERE r.org_id = m.org_id
  AND r.role_key = CASE m.role
      WHEN 'member' THEN 'ap_member'
      WHEN 'approver' THEN 'payment_approver'
      ELSE m.role::text
  END
  AND m.access_role_id IS NULL;

ALTER TABLE public.organization_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_authorities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_delegations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sod_rules ENABLE ROW LEVEL SECURITY;
