from slowapi import Limiter
from slowapi.util import get_remote_address
 
# ── Rate limiter setup ────────────────────────────────────────────────────────
# get_remote_address extracts the client IP from the request.
# This is the key used to track and limit requests.
#
# In production behind a proxy (Nginx, Cloudflare):
# The real IP is in X-Forwarded-For header, not the direct connection IP.
# We handle that in main.py by trusting proxy headers.
#
# Why slowapi?
# - Built specifically for FastAPI/Starlette
# - Uses the same decorator pattern as Flask-Limiter
# - Supports per-route, per-user, per-IP limits
# - In-memory by default (fine for single server MVP)
# - Can swap to Redis backend later for multi-server scaling
#   with one line change: Limiter(key_func=..., storage_uri="redis://...")
 
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],   # global fallback for any undecorated route
)