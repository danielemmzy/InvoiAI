from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings


class QuickBooksOAuth:
    """
    QuickBooks OAuth2 implementation.

    Responsibilities
    ----------------
    • Build authorization URL
    • Exchange authorization code
    • Refresh expired tokens
    • Revoke tokens

    No persistence.

    No repositories.

    No business logic.
    """

    AUTHORIZE_URL = (
        "https://appcenter.intuit.com/connect/oauth2"
    )

    TOKEN_URL = (
        "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    )

    REVOKE_URL = (
        "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
    )

    SCOPE = "com.intuit.quickbooks.accounting"

    def authorization_url(
        self,
        *,
        state: str,
    ) -> str:
        """
        Build OAuth authorization URL.
        """

        params = {
            "client_id": settings.quickbooks_client_id,
            "response_type": "code",
            "scope": self.SCOPE,
            "redirect_uri": settings.quickbooks_redirect_uri,
            "state": state,
        }

        return (
            f"{self.AUTHORIZE_URL}"
            f"?{urlencode(params)}"
        )

    async def exchange_code(
        self,
        *,
        code: str,
    ) -> dict:
        """
        Exchange authorization code
        for OAuth tokens.
        """

        async with httpx.AsyncClient() as client:

            response = await client.post(
                self.TOKEN_URL,
                auth=(
                    settings.quickbooks_client_id,
                    settings.quickbooks_client_secret,
                ),
                headers={
                    "Accept": "application/json",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": (
                        settings.quickbooks_redirect_uri
                    ),
                },
            )

        response.raise_for_status()

        return response.json()

    async def refresh_token(
        self,
        *,
        refresh_token: str,
    ) -> dict:
        """
        Refresh expired access token.
        """

        async with httpx.AsyncClient() as client:

            response = await client.post(
                self.TOKEN_URL,
                auth=(
                    settings.quickbooks_client_id,
                    settings.quickbooks_client_secret,
                ),
                headers={
                    "Accept": "application/json",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )

        response.raise_for_status()

        return response.json()

    async def revoke(
        self,
        *,
        refresh_token: str,
    ) -> bool:
        """
        Disconnect QuickBooks account.
        """

        async with httpx.AsyncClient() as client:

            response = await client.post(
                self.REVOKE_URL,
                auth=(
                    settings.quickbooks_client_id,
                    settings.quickbooks_client_secret,
                ),
                headers={
                    "Accept": "application/json",
                    "Content-Type": (
                        "application/json"
                    ),
                },
                json={
                    "token": refresh_token,
                },
            )

        return response.status_code == 200