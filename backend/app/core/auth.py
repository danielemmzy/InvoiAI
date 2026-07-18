"""
============================================================
app/core/auth.py

Authentication Layer

Responsibilities

✓ Validate JWT
✓ Return authenticated user

Does NOT

✗ Resolve organizations
✗ Check permissions
✗ Load plans
✗ Load features
============================================================
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase import get_supabase
from app.models.context import AuthUser

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

        return AuthUser(
            id=user.id,
            email=user.email or "",
            email_confirmed=user.email_confirmed_at is not None,
            phone=user.phone,
            is_anonymous=user.is_anonymous,
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
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> AuthUser:

    if credentials is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    return validate_access_token(credentials.credentials)