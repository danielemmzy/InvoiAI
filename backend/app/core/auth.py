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
/auth/signup, and /auth/refresh (see routers/auth_v2.py).
The browser frontend now relies exclusively on the cookie — it no
longer has a JS-readable copy of the token to put in a header.
============================================================
"""

from __future__ import annotations

import asyncio
import logging

import jwt

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.context import AuthUser
from app.core.db import run_db
from app.core.error_handler import classify_exception, platform_error
from app.core.supabase import get_supabase
from app.services.auth.mfa_security import totp_verified_at
from app.services.auth import mfa_service
from app.services.auth.verification_service import resolve_email_verified

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================
# JWT Validation
# ============================================================

def validate_access_token(token: str) -> AuthUser:
    """Validate a Supabase access token and return the authenticated user."""
    user, _factors, supabase_verified = validate_token_identity(token)
    from app.services.auth.verification_service import resolve_email_verified

    return user.model_copy(
        update={
            "is_verified": resolve_email_verified(
                user.id,
                supabase_verified=supabase_verified,
            )
        }
    )


def validate_token_identity(token: str) -> tuple[AuthUser, list, bool]:
    """Validate a token and return the identity it proves.

    Returns ``(user, factors, supabase_email_confirmed)``.

    Supabase's ``GET /auth/v1/user`` response already contains the user's
    factors. Re-reading them through ``mfa.list_factors()`` performed a second,
    identical auth-service round trip on every admin request, so the factors
    that arrived with the validated user are returned instead.

    Email-verification state is deliberately *not* resolved here: the caller
    runs it concurrently with the admin-membership lookup, which needs the same
    user id and would otherwise be a third serial round trip.
    """
    try:
        response = get_supabase().auth.get_user(token)

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
            )

        user = response.user

        # Supabase Auth validates this token above. Read assurance claims only
        # after that server-side validation, then carry them to API guards.
        claims = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False, "verify_aud": False},
        )

        # Supabase user metadata is intentionally treated as optional.
        # Organization/role remain None when they are not present in the
        # token metadata; V2 authorization must resolve them from the
        # organization membership/profile layer rather than inventing them.
        app_metadata = getattr(user, "app_metadata", None) or {}
        user_metadata = getattr(user, "user_metadata", None) or {}

        org_id = app_metadata.get("org_id") or user_metadata.get("org_id")
        role = app_metadata.get("role") or user_metadata.get("role")
        plan = app_metadata.get("plan") or user_metadata.get("plan") or "free"

        auth_user = AuthUser(
            id=user.id,
            email=user.email or "",
            org_id=org_id,
            role=role,
            plan=str(plan),
            is_active=True,
            is_verified=False,
            aal=claims.get("aal") if claims.get("aal") in {"aal1", "aal2"} else "aal1",
            token_issued_at=claims.get("iat") if isinstance(claims.get("iat"), int) else None,
            session_id=claims.get("session_id") if isinstance(claims.get("session_id"), str) else None,
            mfa_verified_at=totp_verified_at(claims.get("amr")),
        )

        return (
            auth_user,
            list(getattr(user, "factors", None) or []),
            user.email_confirmed_at is not None,
        )

    except HTTPException:
        raise

    except Exception as exc:
        # External auth-provider outages must not be mislabeled as bad
        # credentials. platform_error() returns None for ordinary 4xx/domain
        # failures and converts only platform/server failures.
        platform_exc = platform_error(exc)
        if platform_exc is not None:
            raise platform_exc from exc

        descriptor = classify_exception(exc)
        logger.warning(
            "Authentication token validation failed: %s (%s)",
            type(exc).__name__,
            descriptor.code,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": descriptor.code,
                "message": descriptor.message,
            },
        ) from exc


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

    user, factors, supabase_verified = await run_db(validate_token_identity, token)

    path = request.url.path
    mfa_exempt = (
        path.startswith("/api/v2/auth/mfa/")
        or path in {"/api/v2/auth/logout", "/api/v2/auth/reset-password"}
        or path.startswith("/api/v2/support/")
    )

    if mfa_exempt:
        # These routes must stay reachable before MFA is enrolled, so the
        # admin-membership lookup would be a wasted query on every request.
        is_verified = await run_db(
            resolve_email_verified,
            user.id,
            supabase_verified=supabase_verified,
        )
        return user.model_copy(update={"is_verified": is_verified})

    # Email-verification state and admin membership depend on the same user id
    # and are independent of each other, so they are resolved concurrently.
    is_verified, is_admin = await asyncio.gather(
        run_db(
            resolve_email_verified,
            user.id,
            supabase_verified=supabase_verified,
        ),
        run_db(mfa_service.has_admin_membership, user.id),
    )
    user = user.model_copy(update={"is_verified": is_verified})

    try:
        if is_admin and not mfa_service.has_verified_totp_factor(factors):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "MFA_ENROLLMENT_REQUIRED",
                    "message": "Set up an authenticator app before using your organization workspace.",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_mfa_enrollment_check_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MFA_STATUS_UNAVAILABLE", "message": "We could not verify your authenticator setup."},
        ) from exc

    return user


async def require_verified_user(
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """Server-side denial for unverified accounts.

    Applied at router level so frontend route filters are never the only
    control. `/auth/*` and workspace onboarding stay reachable so the user can
    finish verification first.
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMAIL_VERIFICATION_REQUIRED",
                "message": (
                    "Verify your email with the six-digit code before "
                    "accessing this workspace."
                ),
            },
        )
    return user
