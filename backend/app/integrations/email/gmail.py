from __future__ import annotations

import base64
from email.message import EmailMessage

from googleapiclient.discovery import build

from app.integrations.google.client import (
    GoogleClientFactory,
)


class GmailService:
    """
    Gmail API wrapper.

    Responsibilities
    ----------------
    • Send emails
    • Read emails
    • Download attachments
    • Search inbox
    • Manage labels

    No business logic.
    No repositories.
    """

    def __init__(self):

        self.client = GoogleClientFactory()

    async def service(
        self,
        *,
        org_id,
    ):

        credentials = await self.client.credentials(
            org_id=org_id,
        )

        return build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

    # =========================================================
    # Send Email
    # =========================================================

    async def send_email(
        self,
        *,
        org_id,
        to: str,
        subject: str,
        body: str,
        html: bool = True,
    ):

        gmail = await self.service(
            org_id=org_id,
        )

        message = EmailMessage()

        message["To"] = to
        message["Subject"] = subject

        if html:
            message.add_alternative(
                body,
                subtype="html",
            )
        else:
            message.set_content(body)

        encoded = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        return (
            gmail.users()
            .messages()
            .send(
                userId="me",
                body={
                    "raw": encoded,
                },
            )
            .execute()
        )

    # =========================================================
    # Read
    # =========================================================

    async def get_message(
        self,
        *,
        org_id,
        message_id: str,
    ):

        gmail = await self.service(
            org_id=org_id,
        )

        return (
            gmail.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

    async def list_messages(
        self,
        *,
        org_id,
        query: str | None = None,
        max_results: int = 25,
    ):

        gmail = await self.service(
            org_id=org_id,
        )

        response = (
            gmail.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=max_results,
            )
            .execute()
        )

        return response.get(
            "messages",
            [],
        )

    # =========================================================
    # Labels
    # =========================================================

    async def list_labels(
        self,
        *,
        org_id,
    ):

        gmail = await self.service(
            org_id=org_id,
        )

        response = (
            gmail.users()
            .labels()
            .list(
                userId="me",
            )
            .execute()
        )

        return response.get(
            "labels",
            [],
        )

    # =========================================================
    # Delete
    # =========================================================

    async def delete_message(
        self,
        *,
        org_id,
        message_id: str,
    ):

        gmail = await self.service(
            org_id=org_id,
        )

        (
            gmail.users()
            .messages()
            .delete(
                userId="me",
                id=message_id,
            )
            .execute()
        )

        return True