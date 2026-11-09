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

import re
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================
# Requests
# ============================================================

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


class SignUpRequest(BaseModel):
    """Registration fields. No company number, tax id, or card is requested."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    mobile: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("mobile")
    @classmethod
    def _valid_mobile(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if not _E164.match(cleaned):
            raise ValueError(
                "Mobile must include a country code, for example +447700900123."
            )
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: EmailStr


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
    verification_email_sent: bool = False
    otp_expires_in_seconds: int | None = None
    resend_cooldown_seconds: int | None = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    user_id: str
    email: EmailStr

    org_id: str | None = None
    plan: str | None = None
    is_verified: bool = True


class UserProfileResponse(BaseModel):
    user_id: str
    email: EmailStr

    org_id: str | None = None
    plan: str | None = None
    is_verified: bool = True
    email_verification_required: bool = False

    usage: dict[str, Any] = Field(default_factory=dict)
