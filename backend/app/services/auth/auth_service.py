from __future__ import annotations

from app.repositories.auth.auth_repository import AuthRepository
from app.repositories.organization.profile_repository import ProfileRepository
from app.services.usage_service import UsageService


class AuthService:
    """V2 authentication application service."""

    def __init__(
        self,
        auth_repository: AuthRepository | None = None,
        profile_repository: ProfileRepository | None = None,
        usage_service: UsageService | None = None,
    ) -> None:
        self.auth = auth_repository or AuthRepository()
        self.profiles = profile_repository or ProfileRepository()
        self.usage = usage_service

    async def signup(self, email, password):
        return await self.auth.signup(email, password)

    async def login(self, email, password):
        return await self.auth.login(email, password)

    async def refresh(self, refresh_token):
        return await self.auth.refresh(refresh_token)

    async def logout(self):
        return await self.auth.logout()

    async def forgot_password(self, email: str, redirect_to: str):
        return await self.auth.forgot_password(email, redirect_to)

    async def resend_signup_confirmation(self, email: str):
        return await self.auth.resend_signup_confirmation(email)

    async def reset_password(self, user_id, password: str):
        return await self.auth.admin_update_password(user_id, password)

    async def profile(self, user):
        """
        Build the /auth/me response.

        API schema requires:
        - user_id -> string
        - org_id  -> string | None
        - usage   -> dictionary
        """

        usage = {}

        if self.usage is not None and getattr(user, "org_id", None):
            try:
                usage = (
                    await self.usage.get_usage_summary(user.org_id)
                    or {}
                )
            except Exception:
                # Do not allow usage analytics failure to break /auth/me.
                usage = {}

        return {
            "user_id": str(user.id),
            "email": user.email,
            "org_id": (
                str(user.org_id)
                if getattr(user, "org_id", None)
                else None
            ),
            "plan": getattr(user, "plan", None),
            "usage": usage,
        }