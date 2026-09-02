from __future__ import annotations

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

    async def signup(self, email: str, password: str):
        return self._client().auth.sign_up(
            {
                "email": email,
                "password": password,
            }
        )

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

    async def logout(self):
        return self._client().auth.sign_out()

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