"""
============================================================
app/core/auth.py

Authentication Layer

Responsibilities

✓ Validate JWT
✓ Return authenticated user

============================================================
SECURITY FIX (see SECURITY_FIXES_APPLIED.md item #2):
get_current_user now accepts the access token from either the
Authorization header (unchanged, still what non-browser clients
like a future mobile app or server-to-server callers should use)
OR an httpOnly `access_token` cookie set by /auth/login,
/auth/signup, and /auth/refresh (see routers/auth_v2.py). The
browser frontend now relies exclusively on the cookie — it no
longer has a JS-readable copy of the token to put in a header.
============================================================
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase import get_supabase
from app.context import AuthUser

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================
# JWT Validation
# ============================================================

def validate_access_token(token: str) -> AuthUser:
    """
    Validate Supabase JWT.
    """

    try:

        response = get_supabase().auth.get_user(token)

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
            )

        user = response.user

        # Supabase user metadata is intentionally treated as optional.
        # Organization/role remain None when they are not present in the
        # token metadata; V2 authorization must resolve them from the
        # organization membership/profile layer rather than inventing them.
        app_metadata = getattr(user, "app_metadata", None) or {}
        user_metadata = getattr(user, "user_metadata", None) or {}

        org_id = app_metadata.get("org_id") or user_metadata.get("org_id")
        role = app_metadata.get("role") or user_metadata.get("role")
        plan = app_metadata.get("plan") or user_metadata.get("plan") or "free"

        return AuthUser(
            id=user.id,
            email=user.email or "",
            org_id=org_id,
            role=role,
            plan=str(plan),
            is_active=True,
            is_verified=user.email_confirmed_at is not None,
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(exc)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


# ============================================================
# FastAPI Dependency
# ============================================================

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> AuthUser:

    # Prefer an explicit Authorization header when present (API keys,
    # service-to-service calls, a future mobile client). Fall back to the
    # httpOnly access_token cookie, which is how the web frontend
    # authenticates now that it no longer stores tokens in JS-readable
    # storage.
    token = credentials.credentials if credentials else request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    return validate_access_token(token)
