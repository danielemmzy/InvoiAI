"""
============================================================
app/services/google/drive_service.py

Google Drive Service

Responsibilities
----------------
- Share spreadsheets
- Manage Drive permissions

No business logic.
============================================================
"""

from __future__ import annotations

from googleapiclient.discovery import build

from app.services.google.credentials import GoogleCredentials


class DriveService:
    """
    Google Drive API wrapper.
    """

    def __init__(self) -> None:

        self.client = build(
            "drive",
            "v3",
            credentials=GoogleCredentials.create(),
        )

    async def share_with_user(
        self,
        *,
        file_id: str,
        email: str,
        role: str = "writer",
    ) -> None:
        """
        Share a Drive file with a user.
        """

        self.client.permissions().create(
            fileId=file_id,
            body={
                "type": "user",
                "role": role,
                "emailAddress": email,
            },
            sendNotificationEmail=False,
        ).execute()