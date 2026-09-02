"""
============================================================
Authentication API Schemas

These schemas are used ONLY for API requests/responses.

They are NOT database models.

They are NOT authentication context models.

Authentication context lives in:

    app/context/auth.py
============================================================
SECURITY FIX (see SECURITY_FIXES_APPLIED.md item #2):
RefreshTokenRequest.refresh_token is now optional. The web
frontend no longer holds the refresh token in JS-readable storage
to put in the request body — /auth/refresh falls back to the
httpOnly refresh_token cookie when the body doesn't supply one.
Non-browser clients can still POST a refresh_token in the body.
============================================================
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ============================================================
# Requests
# ============================================================

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str = Field(..., min_length=8)


# ============================================================
# Responses
# ============================================================

class SignupResponse(BaseModel):
    """Response returned by signup whether email confirmation is enabled or not."""
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user_id: str
    email: EmailStr
    plan: str = "free"
    requires_email_verification: bool = False


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    user_id: str
    email: EmailStr

    org_id: str | None = None
    plan: str | None = None


class UserProfileResponse(BaseModel):
    user_id: str
    email: EmailStr

    org_id: str | None = None
    plan: str | None = None

    usage: dict[str, Any] = Field(default_factory=dict)
