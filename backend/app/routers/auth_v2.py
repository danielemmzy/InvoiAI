from __future__ import annotations

import asyncio
import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.schemas.auth import (
    SignUpRequest,
    LoginRequest,
    RefreshTokenRequest,
    AuthResponse,
    ResendOtpRequest,
    SignupResponse,
    UserProfileResponse,
    VerifyOtpRequest,
    MFAEnrollRequest,
    MFAChallengeRequest,
    MFAVerifyRequest,
    MFARecoveryRequest,
)
from app.core.auth import get_current_user, AuthUser, validate_access_token
from app.core.db import run_db
from app.core.mfa import require_recent_supabase_mfa
from app.core.container import get_container
from app.core.limiter import limiter
from app.core.config import settings
from app.core.error_handler import platform_error
from app.services.auth.google_oauth import build_google_authorization_url
from app.core.supabase import get_user_supabase
from app.services.auth import mfa_service
from app.services.auth.mfa_security import (
    generate_recovery_codes,
    is_recent_aal2,
)

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


async def _response(r) -> AuthResponse:
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

    verification_started = time.perf_counter()
    is_verified = await run_db(
        resolve_email_verified,
        r.user.id,
        supabase_verified=r.user.email_confirmed_at is not None,
    )
    logger.info(
        "login_stage_timing stage=email_verification duration_ms=%d",
        round((time.perf_counter() - verification_started) * 1000),
    )

    return AuthResponse(
        access_token=r.session.access_token,
        refresh_token=r.session.refresh_token,
        user_id=str(r.user.id),
        email=r.user.email,
        plan="free",
        is_verified=is_verified,
    )


async def _mfa_login_state(
    user_id: str,
    access_token: str,
    *,
    factors=None,
) -> tuple[bool, bool]:
    # GoTrue and Postgres are both blocking clients; keep them off the loop.
    membership_started = time.perf_counter()
    is_admin = await run_db(mfa_service.has_admin_membership, user_id)
    logger.info(
        "login_stage_timing stage=mfa_membership duration_ms=%d",
        round((time.perf_counter() - membership_started) * 1000),
    )
    if not is_admin:
        return False, False

    if factors is None:
        # The password grant response carries the user's factors, so the
        # normal path needs no second auth-service call. Older GoTrue
        # responses may omit the field; fall back to listing them rather than
        # assuming MFA is absent.
        factors_started = time.perf_counter()
        listed = await run_db(mfa_service.factors_for_user, access_token)
        logger.info(
            "login_stage_timing stage=mfa_factor_retrieval duration_ms=%d source=auth_api",
            round((time.perf_counter() - factors_started) * 1000),
        )
        factors = listed.all
    else:
        # The password grant already supplied factor state, so no additional
        # Auth API request was needed on this path.
        logger.info(
            "login_stage_timing stage=mfa_factor_retrieval duration_ms=0 source=password_grant",
        )

    if not mfa_service.has_verified_totp_factor(factors):
        return True, False
    return False, True


def _request_access_token(request: Request) -> str:
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not token:
        token = request.cookies.get("access_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return token


async def _require_recovery_or_recent_mfa(user: AuthUser) -> None:
    if is_recent_aal2(user.aal, user.mfa_verified_at):
        return
    if await run_db(
        mfa_service.has_recovery_step_up, user.id, user.session_id
    ):
        return
    raise HTTPException(
        status_code=403,
        detail={"code": "MFA_STEP_UP_REQUIRED", "message": "Verify your authenticator or use a recovery code."},
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
    started = time.perf_counter()

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

    password_auth_ms = (time.perf_counter() - started) * 1000

    if not result.user or not result.session:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
        )

    # Email-verification state and the admin/MFA gate are independent reads,
    # so they run concurrently. Both still execute and enforce their own
    # result; neither is cached.
    auth_task = asyncio.create_task(_response(result))
    checks_started = time.perf_counter()
    try:
        (
            mfa_enrollment_required,
            mfa_challenge_required,
        ) = await _mfa_login_state(
            str(result.user.id),
            result.session.access_token,
            factors=result.user.factors,
        )
    except Exception as exc:
        auth_task.cancel()
        platform_exc = platform_error(exc)
        if platform_exc is not None:
            raise platform_exc from exc
        logger.exception("login_mfa_state_failed")
        raise HTTPException(
            status_code=503,
            detail={"code": "MFA_STATUS_UNAVAILABLE", "message": "We could not verify your authenticator setup."},
        ) from exc

    auth_response = await auth_task
    auth_response.mfa_enrollment_required = mfa_enrollment_required
    auth_response.mfa_challenge_required = mfa_challenge_required

    _set_auth_cookies(response, auth_response.access_token, auth_response.refresh_token)

    logger.info(
        "login_timing password_auth_ms=%d concurrent_checks_ms=%d total_ms=%d",
        round(password_auth_ms),
        round((time.perf_counter() - checks_started) * 1000),
        round((time.perf_counter() - started) * 1000),
    )

    return auth_response


@router.get("/google/start")
@limiter.limit("10/minute")
async def google_oauth_start(
    request: Request,
    redirect_uri: str = Query(..., min_length=1, max_length=2048),
    state: str = Query(..., min_length=32, max_length=128),
    code_challenge: str = Query(..., min_length=43, max_length=128),
):
    try:
        authorize_url = build_google_authorization_url(
            supabase_url=settings.supabase_url,
            anon_key=settings.supabase_anon_key,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            allowed_origin=settings.frontend_app_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(authorize_url, status_code=302)


@router.post("/google/exchange", response_model=AuthResponse)
@limiter.limit("10/minute")
async def google_oauth_exchange(request: Request, body: dict):
    code = body.get("code")
    code_verifier = body.get("code_verifier")
    if (
        not isinstance(code, str)
        or not code
        or not isinstance(code_verifier, str)
        or len(code_verifier) < 43
        or len(code_verifier) > 128
    ):
        raise HTTPException(status_code=400, detail="Invalid OAuth callback.")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/token",
                params={"grant_type": "pkce"},
                headers={"apikey": settings.supabase_anon_key},
                json={"auth_code": code, "code_verifier": code_verifier},
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=401, detail="Google sign-in could not be completed.")
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        if not isinstance(access_token, str) or not isinstance(refresh_token, str):
            raise HTTPException(status_code=401, detail="Google sign-in could not be completed.")

        # validate_access_token performs a blocking GoTrue call and a database
        # read; keep both off the event loop.
        user = await run_db(validate_access_token, access_token)
        if not user.is_verified:
            raise HTTPException(
                status_code=403,
                detail="Verify your Google email before signing in.",
            )
        mfa_enrollment_required, mfa_challenge_required = await _mfa_login_state(
            str(user.id), access_token
        )
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=str(user.id),
            email=user.email,
            plan=user.plan,
            is_verified=True,
            mfa_enrollment_required=mfa_enrollment_required,
            mfa_challenge_required=mfa_challenge_required,
        )
    except HTTPException:
        raise
    except Exception as exc:
        platform_exc = platform_error(exc)
        if platform_exc is not None:
            raise platform_exc from exc
        logger.warning("google_oauth_exchange_failed", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Google sign-in could not be completed.",
        ) from exc


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

    auth_response = await _response(result)
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

    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not token:
        token = request.cookies.get("access_token", "")
    try:
        if token:
            await get_container().auth_service.revoke_sessions(token)
    except Exception as exc:
        logger.exception("password_changed_session_revocation_failed")
        raise HTTPException(
            status_code=503,
            detail=(
                "Your password changed, but we could not revoke existing sessions. "
                "Please contact support."
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
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not token:
        token = request.cookies.get("access_token", "")
    try:
        if token:
            await get_container().auth_service.logout(token)
    except Exception as exc:
        logger.exception("auth_session_revocation_failed")
        raise HTTPException(
            status_code=503,
            detail="Unable to safely sign out. Please try again.",
        ) from exc

    _clear_auth_cookies(response)

    return {
        "message": "Logged out successfully"
    }


# ============================================================
# TOTP MFA AND APP-OWNED RECOVERY CODES
# ============================================================

@router.get("/mfa/factors")
@limiter.limit("30/minute")
async def list_mfa_factors(
    request: Request,
    response: Response,
    user: AuthUser = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    factors = await run_db(mfa_service.factors_for_user, _request_access_token(request))
    return {
        "factors": [
            {
                "id": factor.id,
                "friendly_name": factor.friendly_name,
                "type": factor.factor_type,
                "status": factor.status,
                "created_at": factor.created_at.isoformat(),
            }
            for factor in factors.all
        ],
        "aal": user.aal,
        "step_up_fresh": is_recent_aal2(user.aal, user.mfa_verified_at),
    }


@router.post("/mfa/enroll")
@limiter.limit("5/minute")
async def enroll_mfa_factor(
    request: Request,
    response: Response,
    body: MFAEnrollRequest,
    user: AuthUser = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    token = _request_access_token(request)
    # Building the user client calls the synchronous auth SDK (set_session).
    auth_client = await run_db(get_user_supabase, token)
    current = await run_db(auth_client.auth.mfa.list_factors)
    if current.totp:
        await _require_recovery_or_recent_mfa(user)
    if any(factor.status == "unverified" for factor in current.all):
        raise HTTPException(
            status_code=409,
            detail="Remove the pending authenticator setup before starting another.",
        )
    enrollment = await run_db(
        auth_client.auth.mfa.enroll,
        {
            "factor_type": "totp",
            "issuer": "InvoiAI",
            "friendly_name": body.friendly_name,
        },
    )
    return {
        "factor_id": enrollment.id,
        "friendly_name": enrollment.friendly_name,
        "qr_code": enrollment.totp.qr_code if enrollment.totp else None,
        "secret": enrollment.totp.secret if enrollment.totp else None,
        "uri": enrollment.totp.uri if enrollment.totp else None,
    }


@router.post("/mfa/challenge")
@limiter.limit("5/minute")
async def challenge_mfa_factor(
    request: Request,
    response: Response,
    body: MFAChallengeRequest,
    user: AuthUser = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    auth_client = await run_db(get_user_supabase, _request_access_token(request))
    challenge = await run_db(
        auth_client.auth.mfa.challenge, {"factor_id": body.factor_id}
    )
    return {"challenge_id": challenge.id, "expires_at": challenge.expires_at}


@router.post("/mfa/verify")
@limiter.limit("5/minute")
async def verify_mfa_factor(
    request: Request,
    response: Response,
    body: MFAVerifyRequest,
    user: AuthUser = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    token = _request_access_token(request)
    auth_client = await run_db(get_user_supabase, token)
    factors = await run_db(auth_client.auth.mfa.list_factors)
    factor = next((item for item in factors.all if item.id == body.factor_id), None)
    if factor is None:
        raise HTTPException(status_code=404, detail="Authenticator not found.")

    verified = await run_db(
        auth_client.auth.mfa.verify,
        {
            "factor_id": body.factor_id,
            "challenge_id": body.challenge_id,
            "code": body.code,
        },
    )
    recovery_codes: list[str] | None = None
    if factor.status == "unverified":
        recovery_codes, hashes = generate_recovery_codes()
        await run_db(mfa_service.replace_recovery_codes, user.id, hashes)
    return {
        "access_token": verified.access_token,
        "refresh_token": verified.refresh_token,
        "aal": "aal2",
        "recovery_codes": recovery_codes,
    }


@router.post("/mfa/recovery")
@limiter.limit("5/minute")
async def use_mfa_recovery_code(
    request: Request,
    response: Response,
    body: MFARecoveryRequest,
    user: AuthUser = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    if not user.session_id:
        raise HTTPException(status_code=401, detail="Session could not be verified.")
    if not await run_db(
        mfa_service.consume_recovery_code, user.id, user.session_id, body.code
    ):
        raise HTTPException(
            status_code=400,
            detail={"code": "MFA_INVALID_RECOVERY_CODE", "message": "That recovery code is invalid or has already been used."},
        )
    return {"step_up_granted": True, "expires_in_seconds": 300}


@router.post("/mfa/recovery-codes/regenerate")
@limiter.limit("3/minute")
async def regenerate_mfa_recovery_codes(
    request: Request,
    response: Response,
    user: AuthUser = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    await _require_recovery_or_recent_mfa(user)
    codes, hashes = generate_recovery_codes()
    await run_db(mfa_service.replace_recovery_codes, user.id, hashes)
    return {"recovery_codes": codes}


@router.delete("/mfa/factors/{factor_id}")
@limiter.limit("5/minute")
async def remove_mfa_factor(
    factor_id: str,
    request: Request,
    response: Response,
    user: AuthUser = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    auth_client = await run_db(get_user_supabase, _request_access_token(request))
    factors = await run_db(auth_client.auth.mfa.list_factors)
    factor = next((item for item in factors.all if item.id == factor_id), None)
    if factor is None:
        raise HTTPException(status_code=404, detail="Authenticator not found.")
    if factor.status == "verified":
        require_recent_supabase_mfa(user)
        if await run_db(mfa_service.has_admin_membership, user.id) and len(factors.totp) <= 1:
            raise HTTPException(
                status_code=409,
                detail="Workspace administrators must keep at least one verified authenticator.",
            )
    removed = await run_db(auth_client.auth.mfa.unenroll, {"factor_id": factor_id})
    return {"removed_factor_id": removed.id}


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
