from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.repositories.integration.integration_repository import (
    IntegrationConnectionRepository,
)


class GoogleOAuth:
    """
    Google OAuth2 implementation.

    Responsibilities
    ----------------
    • Build authorization URL
    • Exchange authorization code
    • Refresh expired tokens
    • Persist refreshed tokens
    • Revoke connection

    No Google API business logic.
    """

    AUTHORIZE_URL = (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )

    TOKEN_URL = (
        "https://oauth2.googleapis.com/token"
    )

    REVOKE_URL = (
        "https://oauth2.googleapis.com/revoke"
    )

    SCOPES = [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.org_id = org_id

        self.repository = (
            IntegrationConnectionRepository()
        )

        self.client_id = settings.google_client_id

        self.client_secret = (
            settings.google_client_secret
        )

    # =====================================================
    # Connection
    # =====================================================

    async def connection(self):

        connection = (
            await self.repository.get_google_connection(
                self.org_id,
            )
        )

        if connection is None:

            raise ValueError(
                "Google integration not connected."
            )

        return connection

    async def store_tokens(
        self,
        *,
        connection,
        tokens: dict,
    ):

        connection.access_token = (
            tokens["access_token"]
        )

        if tokens.get("refresh_token"):

            connection.refresh_token = (
                tokens["refresh_token"]
            )

        connection.expires_at = (
            datetime.now(UTC)
            + timedelta(
                seconds=tokens.get(
                    "expires_in",
                    3600,
                )
            )
        )

        await self.repository.update(
            connection,
        )

        return connection

    # =====================================================
    # Authorization
    # =====================================================

    def authorization_url(
        self,
        *,
        state: str,
    ) -> str:

        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": (
                    settings.google_redirect_uri
                ),
                "response_type": "code",
                "scope": " ".join(
                    self.SCOPES
                ),
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
                "state": state,
            }
        )

        return (
            f"{self.AUTHORIZE_URL}"
            f"?{query}"
        )

    # =====================================================
    # Exchange Code
    # =====================================================

    async def exchange_code(
        self,
        *,
        code: str,
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=30,
        ) as client:

            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": (
                        self.client_secret
                    ),
                    "redirect_uri": (
                        settings.google_redirect_uri
                    ),
                    "grant_type": (
                        "authorization_code"
                    ),
                    "code": code,
                },
            )

        response.raise_for_status()

        return response.json()

    # =====================================================
    # Refresh Token
    # =====================================================

    async def refresh_token(
        self,
        *,
        refresh_token: str,
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=30,
        ) as client:

            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": (
                        self.client_secret
                    ),
                    "grant_type": (
                        "refresh_token"
                    ),
                    "refresh_token": (
                        refresh_token
                    ),
                },
            )

        response.raise_for_status()

        return response.json()

    # =====================================================
    # Revoke
    # =====================================================

    async def revoke(
        self,
        *,
        token: str,
    ) -> bool:

        async with httpx.AsyncClient(
            timeout=30,
        ) as client:

            response = await client.post(
                self.REVOKE_URL,
                params={
                    "token": token,
                },
            )

        return response.status_code == 200