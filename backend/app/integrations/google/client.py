from __future__ import annotations

from datetime import UTC
from datetime import datetime

from google.oauth2.credentials import Credentials

from app.integrations.google.oauth import GoogleOAuth


class GoogleClient:
    """
    Authenticated Google client.

    Responsibilities
    ----------------
    • Return valid Google Credentials
    • Automatically refresh expired tokens

    Used by:
        - Drive
        - Sheets
        - Gmail
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.org_id = org_id

        self.oauth = GoogleOAuth(
            org_id=org_id,
        )

    async def credentials(
        self,
    ) -> Credentials:

        connection = await self.oauth.connection()

        access_token = connection.access_token

        refresh_token = connection.refresh_token

        if (
            connection.expires_at
            and connection.expires_at
            <= datetime.now(UTC)
        ):

            tokens = await self.oauth.refresh_token(
                refresh_token=refresh_token,
            )

            connection = await self.oauth.store_tokens(
                connection=connection,
                tokens=tokens,
            )

            access_token = connection.access_token
            refresh_token = connection.refresh_token

        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=self.oauth.TOKEN_URL,
            client_id=self.oauth.client_id,
            client_secret=self.oauth.client_secret,
            scopes=self.oauth.SCOPES,
        )