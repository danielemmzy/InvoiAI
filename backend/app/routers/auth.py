import logging
from fastapi import APIRouter, HTTPException, status, Depends, Request
from app.core.supabase import get_supabase
from app.core.auth import get_current_user, AuthUser
from app.core.limiter import limiter
from app.models.auth import SignUpRequest, LoginRequest, RefreshRequest, AuthResponse, UserProfile
from app.services.usage import get_usage_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=AuthResponse)
@limiter.limit("5/minute")
async def signup(request: Request, body: SignUpRequest):
    """
    Creates a new account.
    Returns JWT tokens so the user is logged in immediately after signup.
    Supabase auto-creates the profile row via the DB trigger.
    """
    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    supabase = get_supabase()

    try:
        response = supabase.auth.sign_up({
            "email": body.email,
            "password": body.password,
        })
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Email may already be registered."
        )

    if not response.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Please try again."
        )

    # Session is None when email confirmation is required in Supabase settings
    if not response.session:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Account created. Please check your email to confirm your account."
        )

    logger.info(f"New signup: {body.email}")

    return AuthResponse(
        access_token=response.session.access_token,
        refresh_token=response.session.refresh_token,
        user_id=response.user.id,
        email=response.user.email,
        plan="free",
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    """
    Logs in and returns JWT tokens.

    access_token  → sent with every API call in the Authorization header
    refresh_token → stored by frontend, used to get new access_token when expired
    """
    supabase = get_supabase()

    try:
        response = supabase.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
    except Exception as e:
        logger.warning(f"Login failed for {body.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not response.user or not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    try:
        profile = (
            supabase.table("profiles")
            .select("plan")
            .eq("id", response.user.id)
            .single()
            .execute()
        )
        plan = profile.data.get("plan", "free") if profile.data else "free"
    except Exception:
        plan = "free"

    logger.info(f"Login: {body.email}")

    return AuthResponse(
        access_token=response.session.access_token,
        refresh_token=response.session.refresh_token,
        user_id=response.user.id,
        email=response.user.email,
        plan=plan,
    )


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit("20/minute")
async def refresh_token(request: Request, body: RefreshRequest):
    """
    Gets a new access_token when the old one expires.
    Frontend calls this automatically when it gets a 401.
    """
    supabase = get_supabase()

    try:
        response = supabase.auth.refresh_session(body.refresh_token)
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again."
        )

    if not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again."
        )

    return AuthResponse(
        access_token=response.session.access_token,
        refresh_token=response.session.refresh_token,
        user_id=response.user.id,
        email=response.user.email,
        plan="free",
    )


@router.post("/logout")
@limiter.limit("20/minute")
async def logout(
    request: Request,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Invalidates the session in Supabase.
    Frontend must also clear stored tokens after calling this.
    Requires: Authorization: Bearer <access_token>
    """
    supabase = get_supabase()
    try:
        supabase.auth.sign_out()
    except Exception as e:
        logger.warning(f"Logout error (non-fatal): {e}")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserProfile)
@limiter.limit("30/minute")
async def get_me(
    request: Request,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Returns current user profile + usage stats.
    Frontend calls this on load to show plan and usage meter.
    Requires: Authorization: Bearer <access_token>
    """
    usage = await get_usage_summary(current_user.id, current_user.plan)

    return UserProfile(
        user_id=current_user.id,
        email=current_user.email,
        plan=current_user.plan,
        usage=usage,
    )