from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase import get_supabase
import logging

logger = logging.getLogger(__name__)

# Reads Authorization: Bearer <token> from every request header
# auto_error=True means missing header = instant 401, route never runs
bearer_scheme = HTTPBearer(auto_error=True)


class AuthUser:
    """
    The authenticated user object injected into every protected route.
    Every route that needs the user just declares:
        current_user: AuthUser = Depends(get_current_user)
    """
    def __init__(self, id: str, email: str, plan: str = "free"):
        self.id = id
        self.email = email
        self.plan = plan


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthUser:
    """
    FastAPI dependency that validates the JWT on every protected request.

    What happens:
    1. Reads the Bearer token from the Authorization header
    2. Sends it to Supabase to verify it is real and not expired
    3. Loads the user's plan from our profiles table
    4. Returns AuthUser — available in the route as current_user

    If token is missing    → 401 (HTTPBearer handles this)
    If token is invalid    → 401
    If token is expired    → 401 (frontend must refresh)
    If everything is fine  → route runs with real user data
    """
    token = credentials.credentials
    supabase = get_supabase()

    try:
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = response.user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user plan from profiles table
    try:
        profile = (
            supabase.table("profiles")
            .select("plan")
            .eq("id", user.id)
            .single()
            .execute()
        )
        plan = profile.data.get("plan", "free") if profile.data else "free"
    except Exception:
        plan = "free"

    return AuthUser(id=user.id, email=user.email, plan=plan)