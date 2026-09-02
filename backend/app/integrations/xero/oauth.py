from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings


class XeroOAuth:
    """
    Xero OAuth2 implementation.

    Responsibilities
    ----------------
    • Build authorization URL
    • Exchange authorization code
    • Refresh expired tokens
    • Retrieve Tenant ID
    • Revoke connection

    No persistence.
    """

    AUTHORIZE_URL = (
        "https://login.xero.com/identity/connect/authorize"
    )

    TOKEN_URL = (
        "https://identity.xero.com/connect/token"
    )

    CONNECTIONS_URL = (
        "https://api.xero.com/connections"
    )

    REVOKE_URL = (
        "https://identity.xero.com/connect/revocation"
    )

    SCOPE = (
        "offline_access "
        "openid "
        "profile "
        "email "
        "accounting.transactions "
        "accounting.contacts "
        "accounting.settings"
    )

    def authorization_url(
        self,
        *,
        state: str,
    ) -> str:

        params = {
            "response_type": "code",
            "client_id": settings.xero_client_id,
            "redirect_uri": settings.xero_redirect_uri,
            "scope": self.SCOPE,
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

        async with httpx.AsyncClient() as client:

            response = await client.post(
                self.TOKEN_URL,
                auth=(
                    settings.xero_client_id,
                    settings.xero_client_secret,
                ),
                headers={
                    "Accept": "application/json",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": (
                        settings.xero_redirect_uri
                    ),
                },
            )

        response.raise_for_status()

        tokens = response.json()

        tenant = await self.get_tenant(
            access_token=tokens["access_token"],
        )

        tokens["tenant_id"] = tenant["tenantId"]
        tokens["tenant_name"] = tenant["tenantName"]

        return tokens

    async def refresh_token(
        self,
        *,
        refresh_token: str,
    ) -> dict:

        async with httpx.AsyncClient() as client:

            response = await client.post(
                self.TOKEN_URL,
                auth=(
                    settings.xero_client_id,
                    settings.xero_client_secret,
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

    async def get_tenant(
        self,
        *,
        access_token: str,
    ) -> dict:

        async with httpx.AsyncClient() as client:

            response = await client.get(
                self.CONNECTIONS_URL,
                headers={
                    "Authorization": (
                        f"Bearer {access_token}"
                    ),
                    "Accept": "application/json",
                },
            )

        response.raise_for_status()

        connections = response.json()

        if not connections:
            raise ValueError(
                "No Xero tenants found."
            )

        return connections[0]

    async def revoke(
        self,
        *,
        refresh_token: str,
    ) -> bool:

        async with httpx.AsyncClient() as client:

            response = await client.post(
                self.REVOKE_URL,
                auth=(
                    settings.xero_client_id,
                    settings.xero_client_secret,
                ),
                headers={
                    "Content-Type": (
                        "application/x-www-form-urlencoded"
                    ),
                },
                data={
                    "token": refresh_token,
                },
            )

        return response.status_code == 200