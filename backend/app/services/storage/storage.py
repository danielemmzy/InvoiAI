from __future__ import annotations

from pathlib import Path

from supabase import Client

from app.core.db import run_db
from app.core.supabase import get_supabase
from app.core.error_handler import PlatformError


class StorageService:
    """
    Storage abstraction.

    Responsibilities
    ----------------
    • Download documents
    • Upload files
    • Delete files
    • Generate signed URLs
    • Verify object existence

    Provider-agnostic.

    Only this service talks to Supabase Storage.
    """

    DOCUMENT_BUCKET = "documents"
    MAX_SIGNED_URL_SECONDS = 300

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
        Download a document from Storage.

        Parameters
        ----------
        path:
            Storage object path.

        Raises
        ------
        StorageApiError
            If the object does not exist or cannot be downloaded.
        """

        try:
            bucket = self.client.storage.from_(
                self.DOCUMENT_BUCKET,
            )
            # The Storage SDK is synchronous; download off the event loop.
            return await run_db(bucket.download, path)
        except Exception as exc:
            raise PlatformError(
                "Document storage is temporarily unavailable.",
                code="STORAGE_UNAVAILABLE",
                status_code=503,
                retryable=True,
                service="supabase_storage",
            ) from exc

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
        Upload a document to Storage.

        The Supabase Storage SDK ultimately sends the upload
        options as HTTP headers. Therefore boolean values must
        not be passed for options such as `upsert`; use the string
        representation expected by the Storage API.

        Returns
        -------
        str
            The Storage object path.
        """

        if not content:
            raise ValueError("Cannot upload an empty document.")

        if not path.strip():
            raise ValueError("Storage path cannot be empty.")

        if not content_type.strip():
            raise ValueError("Content type cannot be empty.")

        bucket = self.client.storage.from_(
            self.DOCUMENT_BUCKET,
        )

        try:
            # The Storage SDK is synchronous; upload off the event loop.
            await run_db(
                bucket.upload,
                path,
                content,
                {
                    "content-type": content_type,
                    "upsert": "false",
                },
            )
        except Exception as exc:
            raise PlatformError(
                "Document storage is temporarily unavailable.",
                code="STORAGE_UNAVAILABLE",
                status_code=503,
                retryable=True,
                service="supabase_storage",
            ) from exc

        return path

    # =========================================================
    # Upload + Verification
    # =========================================================

    async def upload_and_verify(
        self,
        *,
        path: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """
        Upload a document and verify that the object can actually
        be downloaded from Storage.

        This prevents the application from creating a database
        document that points to a missing Storage object.

        If verification fails, the uploaded object is removed
        best-effort before the exception is re-raised.
        """

        await self.upload_document(
            path=path,
            content=content,
            content_type=content_type,
        )

        try:
            stored_content = await self.download_document(path)

            if not stored_content:
                raise RuntimeError(
                    "Storage upload completed but the stored document "
                    "could not be verified."
                )

        except Exception:
            try:
                await self.delete_document(path)
            except Exception:
                # Cleanup is best-effort. The original verification
                # failure is more important and must be preserved.
                pass

            raise

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

        Deletion is intentionally idempotent from the application's
        perspective. If the object is already gone, the Storage
        provider may raise an error; callers performing cleanup
        should normally treat that as best-effort.
        """

        if not path.strip():
            return

        try:
            bucket = self.client.storage.from_(
                self.DOCUMENT_BUCKET,
            )
            # The Storage SDK is synchronous; delete off the event loop.
            await run_db(
                bucket.remove,
                [path],
            )
        except Exception as exc:
            raise PlatformError(
                "Document storage is temporarily unavailable.",
                code="STORAGE_UNAVAILABLE",
                status_code=503,
                retryable=True,
                service="supabase_storage",
            ) from exc

    # =========================================================
    # Signed URLs
    # =========================================================

    async def create_signed_url(
        self,
        *,
        path: str,
        expires_in: int = MAX_SIGNED_URL_SECONDS,
    ) -> str:
        """
        Create a temporary signed URL.
        """

        if not path.strip():
            raise ValueError("Storage path cannot be empty.")

        if not 0 < expires_in <= self.MAX_SIGNED_URL_SECONDS:
            raise ValueError(
                f"expires_in must be between 1 and {self.MAX_SIGNED_URL_SECONDS} seconds."
            )

        try:
            bucket = self.client.storage.from_(
                self.DOCUMENT_BUCKET,
            )
            # The Storage SDK is synchronous; signing off the event loop.
            response = await run_db(
                bucket.create_signed_url,
                path,
                expires_in,
            )
        except Exception as exc:
            raise PlatformError(
                "Document storage is temporarily unavailable.",
                code="STORAGE_UNAVAILABLE",
                status_code=503,
                retryable=True,
                service="supabase_storage",
            ) from exc

        return response["signedURL"]

    # =========================================================
    # Exists
    # =========================================================

    async def exists(
        self,
        path: str,
    ) -> bool:
        """
        Check whether a Storage object exists.

        The Storage list API is used against the object's parent
        folder rather than attempting to construct a public URL.
        """

        if not path.strip():
            return False

        folder = str(Path(path).parent)
        filename = Path(path).name

        try:
            bucket = self.client.storage.from_(
                self.DOCUMENT_BUCKET,
            )
            # The Storage SDK is synchronous; listing off the event loop.
            files = await run_db(bucket.list, folder)
        except Exception as exc:
            raise PlatformError(
                "Document storage is temporarily unavailable.",
                code="STORAGE_UNAVAILABLE",
                status_code=503,
                retryable=True,
                service="supabase_storage",
            ) from exc

        return any(
            str(file.get("name", "")) == filename
            for file in files
        )

    # =========================================================
    # Verify
    # =========================================================

    async def verify_document(
        self,
        path: str,
    ) -> bool:
        """
        Verify that a document can actually be retrieved.

        This is stronger than `exists()` because it verifies the
        object itself rather than only relying on the Storage list
        response.
        """

        if not path.strip():
            return False

        try:
            content = await self.download_document(path)
            return bool(content)
        except Exception:
            return False
