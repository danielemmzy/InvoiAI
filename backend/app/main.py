import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.core.limiter import limiter
from app.routers import upload, invoice, history, export, industries
 
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
 
logger = logging.getLogger(__name__)
 
app = FastAPI(
    title="InvoiAI",
    description="Transform any business document into structured data instantly.",
    version="0.2.0",
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
    allow_origins=["http://localhost:3000", "https://invoiai.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# ── Proxy trust ───────────────────────────────────────────────────────────────
# When deployed behind Cloudflare or Nginx, the real client IP
# comes from X-Forwarded-For header not the direct connection.
# ProxyHeadersMiddleware makes get_remote_address() read the real IP
# so rate limits apply to the actual client, not your proxy server.
# IMPORTANT: only enable this when behind a trusted proxy.
# In local dev it has no effect.
if not settings.debug:
    from starlette.middleware.trustedhost import TrustedHostMiddleware
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
 
# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(invoice.router)
app.include_router(history.router)
app.include_router(export.router)
app.include_router(industries.router)
 
# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": settings.app_name, "version": "0.2.0"}
 
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}