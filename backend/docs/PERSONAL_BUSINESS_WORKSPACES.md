# Personal + Business Workspaces

InvoiAI uses the existing organization tenancy model for both workspace types.

## Model

A user may own:

- one personal workspace
- multiple business workspaces

A personal workspace is an organization with `features.personal_mode = true`.
A business workspace has `features.personal_mode = false`.

The user is an `owner` member of every workspace they create.

## API

### List workspaces

`GET /api/v2/workspaces`

Returns only active memberships belonging to the authenticated user.

### Create workspace

`POST /api/v2/workspaces`

Body:

```json
{
  "type": "business",
  "name": "Acme Construction Ltd",
  "currency": "USD",
  "country": "US"
}
```

For personal:

```json
{
  "type": "personal",
  "currency": "USD"
}
```

The backend prevents duplicate personal workspaces for the same user.
Business workspaces can be created multiple times.

## Tenant isolation

The frontend sends the selected workspace UUID as `X-Org-Id`.
The backend OCM verifies that the authenticated user has an active membership in that organization before any organization-scoped operation proceeds.

The header therefore selects a tenant; it never authorizes access by itself.

## Personal finance isolation

Existing finance tables use:

`owner_type = personal`

and

`owner_id = authenticated user id`

when personal mode is active.

This keeps personal finances separate from business AP data while allowing both experiences to exist under one login.

## Failure handling

Workspace creation uses compensating cleanup. If membership/settings/usage bootstrap fails, the partially created organization is removed so the user is not left with a broken workspace.

For a future high-throughput deployment, this bootstrap can be moved into a single Supabase RPC transaction without changing the public API contract.
