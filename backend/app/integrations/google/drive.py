from __future__ import annotations

from io import BytesIO

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.integrations.google.client import GoogleClient


from app.core.db import execute

class GoogleDriveService:
    """
    Google Drive API wrapper.

    Responsibilities
    ----------------
    • Download files
    • Upload files
    • Search files
    • Read metadata

    No business logic.
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.client = GoogleClient(
            org_id=org_id,
        )

    async def service(self):

        return build(
            "drive",
            "v3",
            credentials=await self.client.credentials(),
            cache_discovery=False,
        )

    # =====================================================
    # Files
    # =====================================================

    async def get_file(
        self,
        *,
        file_id: str,
    ):

        drive = await self.service()

        return (
            (await execute(drive.files()
            .get(
                fileId=file_id,
                fields="*",
            )))
        )

    async def list_folder_files(
        self,
        *,
        folder_id: str,
    ):

        drive = await self.service()

        response = await execute(
            drive.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id,name,mimeType,size,modifiedTime)",
            )
        )

        return response.get(
            "files",
            [],
        )

    async def search_files(
        self,
        *,
        query: str,
    ):

        drive = await self.service()

        response = await execute(
            drive.files()
            .list(
                q=f"name contains '{query}' and trashed=false",
                fields="files(id,name,mimeType)",
            )
        )

        return response.get(
            "files",
            [],
        )

    # =====================================================
    # Download
    # =====================================================

    async def download_file(
        self,
        *,
        file_id: str,
    ) -> bytes:

        drive = await self.service()

        request = (
            drive.files()
            .get_media(
                fileId=file_id,
            )
        )

        buffer = BytesIO()

        downloader = MediaIoBaseDownload(
            buffer,
            request,
        )

        done = False

        while not done:

            _, done = downloader.next_chunk()

        return buffer.getvalue()

    # =====================================================
    # Upload
    # =====================================================

    async def upload_file(
        self,
        *,
        metadata: dict,
        media,
    ):

        drive = await self.service()

        return (
            (await execute(drive.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id,name",
            )))
        )

    async def delete_file(
        self,
        *,
        file_id: str,
    ):

        drive = await self.service()

        await execute(
            drive.files()
            .delete(
                fileId=file_id,
            )
        )

        return True
