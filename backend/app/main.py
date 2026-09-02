from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.core.limiter import limiter
from app.routers import (
    documents, approvals, members, integration_webhooks, integrations,
    copilot, finance, insights, organizations, vendors,
    auth_v2, billing_v2, export_v2, industries_v2, ap, goods_receipts, ap_email, workspaces,
    purchase_orders,
)

from app.core.logging import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.exception_logging import ExceptionLoggingMiddleware
from app.scheduler.runtime import cron_runtime
from app.core.redis import close_redis
from asgi_correlation_id import CorrelationIdMiddleware
 

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cron_runtime.start()
    try:
        yield
    finally:
        await cron_runtime.stop()
        await close_redis()


app = FastAPI(
    title="InvoiAI",
    description="Transform any business document into structured data instantly.",
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
 
# ── Rate limiter ──────────────────────────────────────────────────────────────
# Attach limiter to app state — slowapi reads it from here
# Add SlowAPIMiddleware so limits are enforced on every request
# Register the handler so 429 returns clean JSON not a raw error
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
 
# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://invoiai.com", "https://invoi-ai.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ExceptionLoggingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Request-ID",
)
 
# ── Proxy trust ───────────────────────────────────────────────────────────────
# When deployed behind Cloudflare or Nginx, the real client IP
# comes from X-Forwarded-For header not the direct connection.
# ProxyHeadersMiddleware makes get_remote_address() read the real IP
# so rate limits apply to the actual client, not your proxy server.
# IMPORTANT: only enable this when behind a trusted proxy.
# In local dev it has no effect.
if not settings.debug:
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
 
# ── File size guard ───────────────────────────────────────────────────────────
@app.middleware("http")
async def limit_file_size(request: Request, call_next):
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        return JSONResponse(
            status_code=413,
            content={"detail": f"File too large. Max size is {settings.max_file_size_mb}MB."}
        )
    return await call_next(request)
 
# ── Routers / API versioning ─────────────────────────────────────────────────
# Canonical public API:
#   V1 = frozen compatibility surface
#   V2 = current architecture
#
# Root-mounted routers are retained temporarily for backward compatibility with
# existing clients/tests. New frontend code MUST use /api/v2/*.
# Canonical V2 public API. V1 routers have been removed from the application surface.
V2_ROUTERS = [
    auth_v2.router,
    documents.router,
    approvals.router,
    members.router,
    integration_webhooks.router,
    integrations.router,
    copilot.router,
    finance.router,
    insights.router,
    organizations.router,
    vendors.router,
    billing_v2.router,
    export_v2.router,
    industries_v2.router,
    ap.router,
    goods_receipts.router,
    ap_email.router,
    workspaces.router,
]
for _router in V2_ROUTERS:
    app.include_router(_router, prefix="/api/v2")

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version, "api": {"current": "v2"}}
 
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}