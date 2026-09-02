# Production Redis with Upstash

This backend uses `redis-py` over the standard Redis protocol for:

- distributed scheduler locks
- distributed rate limiting
- cache-aside caching
- temporary coordination state

## 1. Create an Upstash Redis database

1. Open the Upstash Redis console.
2. Create a Redis database.
3. Choose a primary region close to your backend deployment region.
4. Start with the Free plan for development/prototyping.
5. Open the database's **Connect** section and copy the Redis/TCP connection string.

Upstash supports the standard Redis protocol and TLS. For this project, use the
`rediss://...` connection string because the backend uses `redis-py`, not the
Upstash REST SDK.

## 2. Configure the backend

Set this secret in the deployment platform's environment/secret manager:

```text
REDIS_URL=rediss://default:YOUR_PASSWORD@YOUR_ENDPOINT:6379
```

Do not commit the URL/password to Git.

## 3. Verify connectivity

After deployment, run the application's health check or execute a small Python
check using the project's environment:

```powershell
python -c "import asyncio; from app.core.redis import get_redis; print(asyncio.run(get_redis().ping()))"
```

The expected result is:

```text
True
```

## 4. Why the Redis lock matters

The FastAPI process starts the scheduler. With multiple Gunicorn/Uvicorn
workers, each process has its own in-memory cron state. The V2 scheduler now
uses a Redis lock per job:

```text
invoiai:scheduler:lock:<job-name>
```

Only the process that acquires the lock runs the job. The lock is released
with an ownership check and automatically renewed while a long-running job is
executing.

Production defaults:

```text
SCHEDULER_LOCK_ENABLED=true
SCHEDULER_LOCK_TTL_SECONDS=300
SCHEDULER_LOCK_FAIL_OPEN=false
```

Fail-closed is intentional: if Redis is unavailable in production, a worker
must not execute a singleton cron job without coordination.

## 5. Upstash free tier

The current Upstash Redis Free plan is suitable for development and prototypes,
with current published limits shown on Upstash's pricing page. Monitor command,
bandwidth, and storage usage before treating the free tier as a production SLA.

## 6. Security

Use a deployment secret manager for the Redis URL/password. Do not expose it to
the frontend and do not commit it to `.env.example` with real credentials.
