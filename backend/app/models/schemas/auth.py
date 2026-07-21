from typing import Any

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str = Field(..., min_length=8)


# Keep existing names for compatibility
class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: EmailStr
    plan: str


# Keep existing name for compatibility
class UserProfile(BaseModel):
    user_id: str
    email: EmailStr
    plan: str
    usage: dict[str, Any]