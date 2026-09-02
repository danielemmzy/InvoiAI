# V2 Authorization Boundary Hardening

## Request path

Frontend
→ FastAPI authentication
→ Organization Context (membership lookup)
→ membership-derived role/permissions
→ resource ownership / organization scope
→ service
→ repository
→ PostgreSQL/Supabase

The backend does **not** trust `organization_id`, `role`, or `plan` supplied by a client.

### Organization selection

`X-Org-Id` is only a selector. `OrganizationService.build_context()` verifies
that the authenticated user has an active `org_members` row for that
organization. If no header is supplied, the first active membership is used.

### Resource isolation

Organization-owned resources must be checked against `ctx.org_id`.
Personal-finance resources use `(owner_type, owner_id)` and personal mode
uses the authenticated user's UUID as `owner_id`.

### Role/permission isolation

The authoritative role comes from `org_members`, not JWT metadata.
`OrganizationContext.permissions` is derived from that membership role.
V2 routers use centralized permission dependencies for documents, vendors,
finance, insights, billing, AI/copilot, export, approvals and membership
operations.

### Database defense in depth

RLS remains enabled. Because the frontend does not directly query finance or
backend-operational tables, the authorization hardening migration revokes
`anon` and `authenticated` table privileges for those tables. The FastAPI
service-role connection remains the persistence boundary.

Do not enable `FORCE ROW LEVEL SECURITY` globally without reviewing the
service-role/owner behavior first.

## Security tests

`tests/test_v2_authorization_boundary.py` verifies:

- organization context derives role/permissions from membership
- V2 routers do not authorize from token `user.role`
- finance repositories scope by owner type and owner UUID
- insight mutation is organization-scoped
- backend-only finance/operational privileges are revoked

A real two-user/two-organization Supabase isolation test should still be run
against a staging project before production deployment.
