# V2 API Versioning, Redis, Caching and Rate Limiting

## API versioning

- `/api/v2/*` is the canonical authenticated API surface.
- `/api/public/*` is reserved for the token-gated vendor portal.
- The current FastAPI application does not mount a V1 compatibility surface.
- New frontend work must use `/api/v2/*`.
- OAuth callback settings for Google, QuickBooks and Xero now point at `/api/v2/*`.

## Redis

Redis is now an explicit shared infrastructure dependency for:
- distributed rate limiting
- API/application caching
- background queue/pub/sub infrastructure already present in the project
- distributed coordination where existing workers require it

`app/core/redis.py` is the single Redis connection manager. It uses the configured connection pool limit and closes cleanly during application shutdown.

## Caching policy

Cache only derived/read-heavy data that is safe to reconstruct:
- public industry catalog: 24 hours
- organization-scoped vendor lists/searches: 2 minutes
- organization-scoped active insights: 1 minute
- organization current context: 1 minute
- organization/user permissions: 1 minute

Mutations invalidate affected organization cache keys.

Never cache:
- OAuth access/refresh tokens
- passwords or authentication headers
- raw uploaded documents
- provider secrets
- mutable financial records without an explicit invalidation strategy

The cache is cache-aside and PostgreSQL/Supabase remains the source of truth.

## Rate limiting

SlowAPI now uses Redis storage, so limits are shared across API processes/containers.

Global default:
- 200 requests/minute per client address

Stricter V2 endpoints:
- document upload: 10/minute
- copilot chat: 30/minute
- integration OAuth connect: 10/minute
- OAuth callbacks: 20/minute
- vendor and insight reads: 60/minute

Rate limits apply to the mounted V2 and public routes listed above.

## Deployment requirement

Production should run Redis as a managed or HA service and set:

`REDIS_URL=redis://...`

Do not use `flushdb()` from application request paths. Cache invalidation should use targeted keys/prefix scans as implemented by `CacheService.delete_prefix()`.
