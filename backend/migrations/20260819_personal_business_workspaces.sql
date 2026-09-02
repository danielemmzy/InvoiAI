-- InvoiAI: personal/business workspace model
--
-- No new tenant table is introduced. Existing organizations remain the tenant
-- boundary. A personal workspace is simply an organization row with
-- features.personal_mode = true and an owner membership. Business workspaces
-- keep personal_mode = false. This preserves the existing authorization and
-- RLS architecture while allowing one authenticated user to own multiple
-- isolated workspaces.
--
-- Run after the existing organizations/org_members/organization_settings/
-- organization_usage schema is present.

CREATE INDEX IF NOT EXISTS idx_org_members_user_active
    ON public.org_members(user_id, is_active, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_organizations_created_by
    ON public.organizations(created_by, created_at DESC);

-- Existing rows remain business workspaces unless explicitly marked personal.
-- The backend writes the feature flag on creation; no data migration is
-- required for existing customers.
