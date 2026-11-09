from __future__ import annotations

import httpx
from supabase import create_client

from app.core.config import settings


class AuthRepository:
    """
    Persistence boundary for Supabase Auth operations.

    Auth operations use isolated anon-key clients so that a user's
    JWT/session cannot overwrite the backend service-role client's
    authorization state.
    """

    def _client(self):
        return create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )

    async def signup(
        self,
        email: str,
        password: str,
        metadata: dict | None = None,
    ):
        payload: dict = {
            "email": email,
            "password": password,
        }
        if metadata:
            payload["options"] = {"data": metadata}

        return self._client().auth.sign_up(payload)

    async def login(self, email: str, password: str):
        return self._client().auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

    async def refresh(self, refresh_token: str):
        return self._client().auth.refresh_session(
            refresh_token
        )

    async def logout(self, access_token: str):
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/logout",
                params={"scope": "global"},
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
            response.raise_for_status()
            return response

    async def forgot_password(
        self,
        email: str,
        redirect_to: str,
    ):
        return self._client().auth.reset_password_for_email(
            email,
            {
                "redirect_to": redirect_to,
            },
        )

    async def resend_signup_confirmation(
        self,
        email: str,
    ):
        return self._client().auth.resend(
            {
                "type": "signup",
                "email": email,
            }
        )

    async def admin_update_password(
        self,
        user_id: str,
        password: str,
    ):
        from app.core.supabase import get_supabase

        return get_supabase().auth.admin.update_user_by_id(
            str(user_id),
            {
                "password": password,
            },
        )

    async def revoke_sessions(self, access_token: str):
        return await self.logout(access_token)

    async def admin_confirm_email(self, user_id):
        """Mark the identity provider email confirmed after a valid OTP."""
        from app.core.supabase import get_supabase

        return get_supabase().auth.admin.update_user_by_id(
            str(user_id),
            {
                "email_confirm": True,
            },
        )
