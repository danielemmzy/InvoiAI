from __future__ import annotations

from uuid import UUID

from app.core.enum.database import (
    DocumentStatus,
    PipelineStage,
)

from app.models.domain.document import Document
from app.repositories.document.document_repository import DocumentRepository

class DocumentService:
    """
    Business logic for document management.

    Responsibilities
    ----------------
    - Document creation
    - Duplicate detection
    - Pipeline orchestration
    - Archive / restore
    - Retry handling
    - Export tracking

    No SQL belongs here.
    """

    def __init__(
        self,
        repository: DocumentRepository,
    ):
        self.repository = repository

    async def create_document(
        self,
        document: Document,
    ) -> Document:
        """
        Create a document.

        Raises
        ------
        ValueError
            If a duplicate already exists.
        """

        if document.file_hash:

            duplicate = await self.repository.get_document_by_hash(
                document.org_id,
                document.file_hash,
            )

            if duplicate:
                raise ValueError(
                    "Document already exists."
                )

        return await self.repository.create_document(
            document,
        )

    async def get_document(
        self,
        document_id: UUID,
    ) -> Document:

        document = await self.repository.get_document(
            document_id,
        )

        if document is None:
            raise ValueError(
                "Document not found."
            )

        return document

    async def get_document_by_number(
        self,
        org_id: UUID,
        document_number: str,
    ) -> Document | None:

        return await self.repository.get_document_by_number(
            org_id,
            document_number,
        )
    async def list_documents(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        return await self.repository.list_documents(
            org_id,
            limit,
            offset,
        )

        # =========================================================
    # Pipeline
    # =========================================================

    async def update_pipeline_stage(
        self,
        document_id: UUID,
        stage: PipelineStage,
    ) -> Document:

        document = await self.get_document(
            document_id,
        )

        if document.pipeline_stage == stage:
            return document

        updated = await self.repository.update_pipeline_stage(
            document_id,
            stage,
        )

        if updated is None:
            raise ValueError(
                "Unable to update pipeline stage."
            )

        return updated

    async def mark_completed(
        self,
        document_id: UUID,
    ) -> Document:

        document = await self.get_document(
            document_id,
        )

        if document.status == DocumentStatus.COMPLETED:
            return document

        updated = await self.repository.mark_completed(
            document_id,
        )

        if updated is None:
            raise ValueError(
                "Unable to mark document completed."
            )

        return updated

    async def mark_failed(
        self,
        document_id: UUID,
        error_message: str,
    ) -> Document:

        if not error_message:
            raise ValueError(
                "Error message cannot be empty."
            )

        updated = await self.repository.mark_failed(
            document_id,
            error_message,
        )

        if updated is None:
            raise ValueError(
                "Unable to mark document failed."
            )

        return updated

    async def retry_processing(
        self,
        document_id: UUID,
    ) -> Document:

        document = await self.get_document(
            document_id,
        )

        if document.status != DocumentStatus.FAILED:
            raise ValueError(
                "Only failed documents can be retried."
            )

        await self.repository.increment_retry(
            document_id,
        )

        updated = await self.repository.update_pipeline_stage(
            document_id,
            PipelineStage.UPLOADED,
        )

        if updated is None:
            raise ValueError(
                "Unable to restart pipeline."
            )

        return updated

        # =========================================================
    # Archive
    # =========================================================

    async def archive_document(
        self,
        document_id: UUID,
        archived_by: UUID,
        reason: str | None = None,
    ) -> Document:

        document = await self.get_document(
            document_id,
        )

        if document.is_archived:
            return document

        archived = await self.repository.archive_document(
            document_id,
            archived_by,
            reason,
        )

        if archived is None:
            raise ValueError(
                "Unable to archive document."
            )

        return archived

    async def restore_document(
        self,
        document_id: UUID,
    ) -> Document:

        document = await self.get_document(
            document_id,
        )

        if not document.is_archived:
            return document

        restored = await self.repository.restore_document(
            document_id,
        )

        if restored is None:
            raise ValueError(
                "Unable to restore document."
            )

        return restored

    # =========================================================
    # Export
    # =========================================================

    async def update_export(
        self,
        document_id: UUID,
        export_format: str,
        exported_by: UUID,
    ) -> Document:

        if not export_format.strip():
            raise ValueError(
                "Export format is required."
            )

        updated = await self.repository.update_export(
            document_id,
            export_format,
            exported_by,
        )

        if updated is None:
            raise ValueError(
                "Unable to update export information."
            )

        return updated

    # =========================================================
    # Status Queries
    # =========================================================

    async def list_archived_documents(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        return await self.repository.list_archived_documents(
            org_id,
            limit,
            offset,
        )

    async def list_vendor_documents(
        self,
        org_id: UUID,
        vendor_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        return await self.repository.list_vendor_documents(
            org_id,
            vendor_id,
            limit,
            offset,
        )

    async def list_by_status(
        self,
        org_id: UUID,
        status: DocumentStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        return await self.repository.list_by_status(
            org_id,
            status,
            limit,
            offset,
        )

    async def list_by_pipeline_stage(
        self,
        org_id: UUID,
        stage: PipelineStage,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        return await self.repository.list_by_pipeline_stage(
            org_id,
            stage,
            limit,
            offset,
        )

        # =========================================================
    # Statistics
    # =========================================================

    async def count_documents(
        self,
        org_id: UUID,
    ) -> int:

        return await self.repository.count_documents(
            org_id,
        )

    async def count_processing(
        self,
        org_id: UUID,
    ) -> int:

        return await self.repository.count_processing(
            org_id,
        )

    # =========================================================
    # Duplicate Detection
    # =========================================================

    async def document_exists(
        self,
        org_id: UUID,
        file_hash: str,
    ) -> bool:

        document = await self.repository.get_document_by_hash(
            org_id,
            file_hash,
        )

        return document is not None

    async def find_duplicate(
        self,
        org_id: UUID,
        file_hash: str,
    ) -> Document | None:

        return await self.repository.get_document_by_hash(
            org_id,
            file_hash,
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def retry_processing(
        self,
        document_id: UUID,
    ) -> Document:

        document = await self.get_document(
            document_id,
        )

        if document.status != DocumentStatus.FAILED:
            raise ValueError(
                "Only failed documents can be retried."
            )

        await self.repository.increment_retry(
            document_id,
        )

        updated = await self.repository.update_pipeline_stage(
            document_id,
            PipelineStage.QUEUED,
        )

        if updated is None:
            raise ValueError(
                "Unable to queue document for retry."
            )

        return updated

    async def exists(
        self,
        document_id: UUID,
    ) -> bool:

        return (
            await self.repository.get_document(
                document_id,
            )
            is not None
        )

    async def validate_document_number(
        self,
        org_id: UUID,
        document_number: str,
        ignore_document_id: UUID | None = None,
    ) -> bool:

        existing = await self.repository.get_document_by_number(
            org_id,
            document_number,
        )

        if existing is None:
            return True

        if (
            ignore_document_id
            and existing.id == ignore_document_id
        ):
            return True

        return False

    async def can_archive(
        self,
        document_id: UUID,
    ) -> bool:

        document = await self.get_document(
            document_id,
        )

        return not document.is_archived

    async def can_restore(
        self,
        document_id: UUID,
    ) -> bool:

        document = await self.get_document(
            document_id,
        )

        return document.is_archived