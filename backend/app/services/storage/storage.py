from __future__ import annotations

from pathlib import Path

from supabase import Client

from app.core.supabase import get_supabase


class StorageService:
    """
    Storage abstraction.

    Responsibilities
    ----------------
    • Download documents
    • Upload files
    • Delete files
    • Generate signed URLs

    Provider-agnostic.

    Only this service talks to Supabase Storage.
    """

    DOCUMENT_BUCKET = "documents"

    def __init__(
        self,
        client: Client | None = None,
    ) -> None:

        self.client = client or get_supabase()

    # =========================================================
    # Download
    # =========================================================

    async def download_document(
        self,
        path: str,
    ) -> bytes:
        """
        Download a document from storage.

        Parameters
        ----------
        path:
            Storage object path.
        """

        return self.client.storage.from_(
            self.DOCUMENT_BUCKET,
        ).download(path)

    # =========================================================
    # Upload
    # =========================================================

    async def upload_document(
        self,
        *,
        path: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """
        Upload a document.

        Returns storage path.
        """

        self.client.storage.from_(
            self.DOCUMENT_BUCKET,
        ).upload(
            path,
            content,
            {
                "content-type": content_type,
                "upsert": True,
            },
        )

        return path

    # =========================================================
    # Delete
    # =========================================================

    async def delete_document(
        self,
        path: str,
    ) -> None:
        """
        Delete a stored document.
        """

        self.client.storage.from_(
            self.DOCUMENT_BUCKET,
        ).remove(
            [path],
        )

    # =========================================================
    # Signed URLs
    # =========================================================

    async def create_signed_url(
        self,
        *,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Create a temporary signed URL.
        """

        response = self.client.storage.from_(
            self.DOCUMENT_BUCKET,
        ).create_signed_url(
            path,
            expires_in,
        )

        return response["signedURL"]

    # =========================================================
    # Exists
    # =========================================================

    async def exists(
        self,
        path: str,
    ) -> bool:
        """
        Check whether a file exists.
        """

        folder = str(Path(path).parent)
        filename = Path(path).name

        files = self.client.storage.from_(
            self.DOCUMENT_BUCKET,
        ).list(folder)

        return any(
            file["name"] == filename
            for file in files
        )