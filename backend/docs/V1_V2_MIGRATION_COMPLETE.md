# V1 → V2 Migration

The frontend now targets `/api/v2` through the Axios base client.
V1 FastAPI routers were removed from the application and their route modules deleted.

## Verification checklist
- Search frontend for absolute V1 paths.
- Run `npm run build`.
- Run backend `pytest -q`.
- Verify OAuth callbacks use `/api/v2`.
- Verify Stripe dashboard webhook URL is changed to `/api/v2/stripe/webhook` once the V2 billing webhook handler is deployed.

The Stripe webhook handler remains an integration concern and should be verified against the V2 billing event processor before production rollout.
