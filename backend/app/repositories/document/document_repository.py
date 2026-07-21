"""
============================================================
app/repositories/document/document_repository.py

Document repository.

Responsible ONLY for document persistence.

Responsibilities
----------------
- Create documents
- Retrieve documents
- Search documents
- Update pipeline state
- Link vendors
- Store AI results

No OCR.
No AI.
No business logic.
============================================================
"""

from __future__ import annotations

from app.repositories.base import BaseRepository

from backend.app.core.enum.enums import (
    DocumentStatus,
    PipelineStage,
)


class DocumentRepository(BaseRepository):

    table_name = "documents"

    def __init__(self):
        super().__init__()

    # =========================================================
    # Creation
    # =========================================================

    async def create_document(
        self,
        document_data: dict,
    ):
        """
        Create a new document.
        """

        return (
            self.table()
            .insert(document_data)
            .execute()
        )
    
        # =========================================================
    # Retrieval
    # =========================================================

    async def get_document(
        self,
        document_id: str,
    ):
        """
        Retrieve a document by its ID.
        """

        return (
            self.table()
            .select("*")
            .eq("id", document_id)
            .single()
            .execute()
        )

    async def get_document_by_number(
        self,
        org_id: str,
        document_number: str,
    ):
        """
        Retrieve a document by its business document number.
        """

        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("document_number", document_number)
            .limit(1)
            .execute()
        )

    async def get_document_by_hash(
        self,
        org_id: str,
        file_hash: str,
    ):
        """
        Retrieve a document by its file hash.

        Used for duplicate detection.
        """

        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("file_hash", file_hash)
            .limit(1)
            .execute()
        )
        # =========================================================
    # Listing & Search
    # =========================================================

    async def list_documents(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        List organization documents.
        """

        return (
            self.table()
            .select("*", count="exact")
            .eq("org_id", org_id)
            .eq("is_archived", False)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    async def list_archived_documents(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        List archived documents.
        """

        return (
            self.table()
            .select("*", count="exact")
            .eq("org_id", org_id)
            .eq("is_archived", True)
            .order("archived_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    async def list_vendor_documents(
        self,
        org_id: str,
        vendor_id: str,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        List all documents for one vendor.
        """

        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("vendor_id", vendor_id)
            .order("document_date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    async def list_by_status(
        self,
        org_id: str,
        status: str,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        List documents by processing status.
        """

        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("status", status)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    async def list_by_pipeline_stage(
        self,
        org_id: str,
        stage: str,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        List documents currently in a pipeline stage.
        """

        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("pipeline_stage", stage)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        # =========================================================
    # Pipeline State
    # =========================================================

    async def mark_processing(
        self,
        document_id: str,
    ):
        """
        Mark document as processing.
        """

        return (
            self.table()
            .update(
                {
                    "status": DocumentStatus.PROCESSING.value,
                }
            )
            .eq("id", document_id)
            .execute()
        )

    async def update_pipeline_stage(
        self,
        document_id: str,
        stage: PipelineStage,
    ):
        """
        Update pipeline stage.
        """

        return (
            self.table()
            .update(
                {
                    "pipeline_stage": stage.value,
                }
            )
            .eq("id", document_id)
            .execute()
        )

    async def mark_completed(
        self,
        document_id: str,
    ):
        """
        Mark processing complete.
        """

        return (
            self.table()
            .update(
                {
                    "status": DocumentStatus.COMPLETED.value,
                    "pipeline_stage": PipelineStage.COMPLETED.value,
                }
            )
            .eq("id", document_id)
            .execute()
        )

    async def mark_failed(
        self,
        document_id: str,
        error_message: str,
    ):
        """
        Mark processing failed.
        """

        return (
            self.table()
            .update(
                {
                    "status": DocumentStatus.FAILED.value,
                    "pipeline_stage": PipelineStage.FAILED.value,
                    "error_message": error_message,
                }
            )
            .eq("id", document_id)
            .execute()
        )

    async def increment_retry(
        self,
        document_id: str,
    ):
        """
        Increment retry count using a database RPC.
        """

        return (
            await self.db.rpc(
                "increment_document_retry",
                {
                    "p_document_id": document_id,
                },
            ).execute()
        )
    
        # =========================================================
    # Archive
    # =========================================================

    async def archive_document(
        self,
        document_id: str,
        archived_by: str,
        reason: str | None = None,
    ):
        """
        Archive a document.
        """

        return (
            self.table()
            .update(
                {
                    "is_archived": True,
                    "archived_by": archived_by,
                    "archive_reason": reason,
                    "archived_at": "now()",
                }
            )
            .eq("id", document_id)
            .execute()
        )

    async def restore_document(
        self,
        document_id: str,
    ):
        """
        Restore an archived document.
        """

        return (
            self.table()
            .update(
                {
                    "is_archived": False,
                    "archived_by": None,
                    "archive_reason": None,
                    "archived_at": None,
                }
            )
            .eq("id", document_id)
            .execute()
        )
    
        # =========================================================
    # Export
    # =========================================================

    async def update_export(
        self,
        document_id: str,
        export_format: str,
        exported_by: str,
    ):
        """
        Record export metadata.
        """

        return (
            self.table()
            .update(
                {
                    "last_exported_format": export_format,
                    "last_exported_by": exported_by,
                    "last_exported_at": "now()",
                }
            )
            .eq("id", document_id)
            .execute()
        )
    
        # =========================================================
    # Statistics
    # =========================================================

    async def count_documents(
        self,
        org_id: str,
    ):
        """
        Count documents for an organization.
        """

        return (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", org_id)
            .execute()
        )

    async def count_processing(
        self,
        org_id: str,
    ):
        """
        Count documents currently processing.
        """

        return (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", org_id)
            .eq(
                "status",
                DocumentStatus.PROCESSING.value,
            )
            .execute()
        )
    
        # =========================================================
    # Exists
    # =========================================================

    async def exists(
        self,
        document_id: str,
    ) -> bool:
        """
        Check whether a document exists.
        """

        response = (
            self.table()
            .select("id")
            .eq("id", document_id)
            .limit(1)
            .execute()
        )

        return bool(response.data)