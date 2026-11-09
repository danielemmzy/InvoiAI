from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.core.limiter import limiter
from app.routers import (
    documents, approvals, members, integration_webhooks, integrations,
    copilot, finance, insights, organizations, vendors,
    auth_v2, billing_v2, export_v2, industries_v2, ap, goods_receipts, ap_email, workspaces,
    purchase_orders, ap_workflow, vendor_portal, vendor_credits, organization_access, organization_settings,
    ops,
)

from app.core.logging import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.exception_logging import ExceptionLoggingMiddleware
from app.core.error_handler import error_response, register_error_handlers
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
app.state.limiter = limiter
register_error_handlers(app)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ─────────────────────────────────────────────────────────────────────
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
# When deployed behind Cloudflare or Nginx, the real client IP comes from
# X-Forwarded-For. Only enable this when the deployment is behind a trusted
# proxy. In local development it has no effect.
if not settings.debug:
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# ── File size guard ───────────────────────────────────────────────────────────
@app.middleware("http")
async def limit_file_size(request: Request, call_next):
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    content_length = request.headers.get("content-length")

    if content_length:
        try:
            declared_length = int(content_length)
        except (TypeError, ValueError):
            return error_response(
                request,
                HTTPException(
                    status_code=400,
                    detail={
                        "code": "INVALID_CONTENT_LENGTH",
                        "message": "The request content length is invalid.",
                    },
                ),
                force_log=False,
            )

        if declared_length < 0:
            return error_response(
                request,
                HTTPException(
                    status_code=400,
                    detail={
                        "code": "INVALID_CONTENT_LENGTH",
                        "message": "The request content length is invalid.",
                    },
                ),
                force_log=False,
            )

        if declared_length > max_bytes:
            return error_response(
                request,
                HTTPException(
                    status_code=413,
                    detail={
                        "code": "FILE_TOO_LARGE",
                        "message": f"File too large. Max size is {settings.max_file_size_mb}MB.",
                    },
                ),
                force_log=False,
            )

    return await call_next(request)

# ── Routers / API versioning ─────────────────────────────────────────────────
# Canonical V2 public API. V1 routers have been removed from the application
# surface.
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
    ap_workflow.router,
    ap_email.router,
    workspaces.router,
    purchase_orders.router,
    organization_access.router,
    organization_settings.router,
    ops.router,
]
for _router in V2_ROUTERS:
    app.include_router(_router, prefix="/api/v2")

# Public, token-gated — deliberately NOT under /api/v2 (no
# OrganizationContext/session auth applies to this router).
app.include_router(vendor_portal.router, prefix="/api/public")
app.include_router(vendor_credits.router, prefix="/api/v2")

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version, "api": {"current": "v2"}}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
