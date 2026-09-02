"""
============================================================
app/services/google/credentials.py

Google Credentials

Responsibilities
----------------
- Build Google service account credentials
- Provide authenticated Google API credentials

No business logic.
No repositories.
============================================================
"""

from __future__ import annotations

from google.oauth2.service_account import Credentials

from app.core.config import settings


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleCredentials:
    """
    Creates Google service account credentials.
    """

    @staticmethod
    def create() -> Credentials:
        """
        Build credentials from environment variables.
        """

        credentials_info = {
            "type": "service_account",
            "project_id": settings.google_project_id,
            "private_key_id": settings.google_private_key_id,
            "private_key": settings.google_private_key.replace(
                "\\n",
                "\n",
            ),
            "client_email": settings.google_service_account_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        return Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES,
        )