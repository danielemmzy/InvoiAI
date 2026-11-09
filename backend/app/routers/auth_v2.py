from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.schemas.auth import (
    SignUpRequest,
    LoginRequest,
    RefreshTokenRequest,
    AuthResponse,
    ResendOtpRequest,
    SignupResponse,
    UserProfileResponse,
    VerifyOtpRequest,
)
from app.core.auth import get_current_user, AuthUser
from app.core.container import get_container
from app.core.limiter import limiter
from app.core.config import settings
from app.core.error_handler import platform_error

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

# ============================================================
# SECURITY FIX (see SECURITY_FIXES_APPLIED.md item #2)
#
# Every endpoint that issues or rotates a session now ALSO sets the
# access and refresh tokens as httpOnly cookies, in addition to
# returning them in the JSON body (kept for any non-browser client).
# The web frontend no longer reads these tokens out of the JSON body
# to store them anywhere JS can reach — it relies entirely on the
# cookies, which an XSS payload cannot read.
#
# Cookie names are `access_token` / `refresh_token` on purpose:
# middleware.ts on the frontend already reads a cookie literally
# named `access_token` to gate /dashboard and /workspace routes, so
# this requires zero changes there.
# ============================================================

_ACCESS_TOKEN_MAX_AGE = 60 * 60          # 1 hour — matches Supabase's default access token lifetime
_REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

def _is_secure_cookie() -> bool:
    """
    HTTPS is required for Secure cookies in real deployments.

    Local HTTP development must be allowed to use authentication
    cookies without requiring HTTPS.
    """
    environment = settings.environment.strip().lower()

    return environment in {
        "production",
        "prod",
        "staging",
    }


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = _is_secure_cookie()
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=_ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=_REFRESH_TOKEN_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _response(r) -> AuthResponse:
    """
    Convert Supabase Auth response into our API response schema.

    Supabase returns UUID objects for user IDs.
    Our API schema expects strings.
    """

    if not r.user or not r.session:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
        )

    from app.services.auth.verification_service import resolve_email_verified

    return AuthResponse(
        access_token=r.session.access_token,
        refresh_token=r.session.refresh_token,
        user_id=str(r.user.id),
        email=r.user.email,
        plan="free",
        is_verified=resolve_email_verified(
            r.user.id,
            supabase_verified=r.user.email_confirmed_at is not None,
        ),
    )


# ============================================================
# SIGNUP
# ============================================================

@router.post(
    "/signup",
    response_model=SignupResponse,
)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    response: Response,
    body: SignUpRequest,
):
    metadata = {
        "first_name": body.first_name,
        "last_name": body.last_name,
    }
    if body.mobile:
        metadata["mobile"] = body.mobile

    try:
        result = await get_container().auth_service.signup(
            body.email,
            body.password,
            metadata,
        )

    except Exception as exc:
        platform_exc = platform_error(exc)
        if platform_exc is not None:
            raise platform_exc from exc
        raise HTTPException(
            status_code=400,
            detail="Signup could not be completed.",
        ) from exc

    if not result.user:
        raise HTTPException(status_code=400, detail="Signup failed")

    # Whether or not Supabase issued a session, access waits for the
    # six-digit email code. No auth cookies are set here on purpose.
    otp: dict | None = None
    try:
        otp = await get_container().email_verification_service.issue(
            user_id=result.user.id,
            email=result.user.email or body.email,
            first_name=body.first_name,
        )
    except Exception:
        logger.exception("signup_verification_challenge_failed")
        # The account exists; the user can request a new code from the
        # verification screen instead of losing the signup.
        otp = None

    return SignupResponse(
        user_id=str(result.user.id),
        email=result.user.email or body.email,
        plan="free",
        requires_email_verification=True,
        verification_email_sent=bool(otp and otp.get("code_sent")),
        otp_expires_in_seconds=(
            int(otp["expires_in_seconds"]) if otp else None
        ),
        resend_cooldown_seconds=(
            int(otp["resend_cooldown_seconds"]) if otp else None
        ),
    )


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=AuthResponse,
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
):
    try:
        result = await get_container().auth_service.login(
            body.email,
            body.password,
        )

    except Exception as exc:
        platform_exc = platform_error(exc)
        if platform_exc is not None:
            raise platform_exc from exc
        text = str(exc).lower()
        if "confirm" in text or "verified" in text:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "EMAIL_VERIFICATION_REQUIRED",
                    "message": (
                        "Verify your email with the six-digit code before "
                        "signing in."
                    ),
                },
            ) from exc
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        ) from exc

    auth_response = _response(result)
    _set_auth_cookies(response, auth_response.access_token, auth_response.refresh_token)
    return auth_response


# ============================================================
# REFRESH
# ============================================================

@router.post(
    "/refresh",
    response_model=AuthResponse,
)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    response: Response,
    body: RefreshTokenRequest,
):
    # The web frontend no longer has a JS-readable refresh token to put
    # in the body — it POSTs an empty body and relies on the httpOnly
    # refresh_token cookie instead. Non-browser clients can still pass
    # refresh_token explicitly.
    refresh_token = body.refresh_token or request.cookies.get("refresh_token")

    if not refresh_token:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again.",
        )

    try:
        result = await get_container().auth_service.refresh(
            refresh_token,
        )

    except Exception as exc:
        platform_exc = platform_error(exc)
        if platform_exc is not None:
            raise platform_exc from exc
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again.",
        ) from exc

    if not result.session:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again.",
        )

    auth_response = _response(result)
    _set_auth_cookies(response, auth_response.access_token, auth_response.refresh_token)
    return auth_response


# ============================================================
# FORGOT PASSWORD
# ============================================================

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    response: Response,
    body: dict,
):
    email = str(
        body.get("email", "")
    ).strip().lower()

    if "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid email address",
        )

    redirect_to = (
        f"{settings.frontend_app_url.rstrip('/')}"
        "/reset-password"
    )

    # Do not reveal whether an email exists.
    try:
        await get_container().auth_service.forgot_password(
            email,
            redirect_to,
        )
    except Exception:
        pass

    return {
        "message": (
            "If an account exists for that email, "
            "a password reset link has been sent."
        )
    }


# ============================================================
# SIX-DIGIT EMAIL OTP
# ============================================================

@router.post("/verify-otp")
@limiter.limit("10/minute")
async def verify_otp(
    request: Request,
    response: Response,
    body: VerifyOtpRequest,
):
    result = await get_container().email_verification_service.verify(
        email=str(body.email),
        code=body.code,
    )

    if result.status == "verified":
        return {
            "verified": True,
            "message": result.message,
        }

    status_code = {
        "locked": 423,
        "delivery_failed": 503,
    }.get(result.status, 400)

    raise HTTPException(
        status_code=status_code,
        detail={
            "code": f"OTP_{result.status.upper()}",
            "message": result.message,
        },
    )


@router.post("/resend-otp")
@limiter.limit("3/minute")
async def resend_otp(
    request: Request,
    response: Response,
    body: ResendOtpRequest,
):
    # Always returns the same shape, whether or not the account exists.
    return await get_container().email_verification_service.resend(
        email=str(body.email),
    )


# ============================================================
# RESEND VERIFICATION (migration alias for the old link flow)
# ============================================================

@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    response: Response,
    body: ResendOtpRequest,
):
    return await get_container().email_verification_service.resend(
        email=str(body.email),
    )


# ============================================================
# RESET PASSWORD
# ============================================================

@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    response: Response,
    body: dict,
    user: AuthUser = Depends(get_current_user),
):
    password = str(
        body.get("password", "")
    )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters",
        )

    try:
        await get_container().auth_service.reset_password(
            user.id,
            password,
        )

    except Exception as exc:
        platform_exc = platform_error(exc)
        if platform_exc is not None:
            raise platform_exc from exc
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to reset password. "
                "Please request a new link."
            ),
        ) from exc

    return {
        "message": "Password updated successfully."
    }


# ============================================================
# LOGOUT
# ============================================================

@router.post("/logout")
@limiter.limit("20/minute")
async def logout(
    request: Request,
    response: Response,
    user: AuthUser = Depends(get_current_user),
):
    try:
        await get_container().auth_service.logout()
    except Exception:
        pass

    _clear_auth_cookies(response)

    return {
        "message": "Logged out successfully"
    }


# ============================================================
# CURRENT USER
# ============================================================

@router.get(
    "/me",
    response_model=UserProfileResponse,
)
@limiter.limit("30/minute")
async def me(
    request: Request,
    response: Response,
    user: AuthUser = Depends(get_current_user),
):
    return await get_container().auth_service.profile(user)
