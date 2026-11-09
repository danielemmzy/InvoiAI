from __future__ import annotations

import hashlib
from pathlib import PurePath
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.enum.database import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    PipelineStage,
)
from app.models.domain.document import Document
from app.services.document.document_service import DocumentService
from app.services.storage.attachment_scanner import (
    QUARANTINE_PREFIX,
    get_attachment_scanner,
)
from app.services.storage.file_inspection import inspect_upload
from app.services.storage.storage import StorageService


class DuplicateDocumentError(Exception):
    """Raised when an uploaded file already exists for the organization."""

    def __init__(
        self,
        message: str = "A document with the same file already exists.",
        *,
        existing_document_id: UUID | None = None,
        existing_file_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.existing_document_id = existing_document_id
        self.existing_file_name = existing_file_name


class DocumentUploadService:
    """Application service for V2 document intake.

    Responsibilities:
    - Validate uploaded files.
    - Calculate the SHA-256 content hash.
    - Detect duplicate documents.
    - Store the original file.
    - Create the initial document record.
    - Clean up storage when database creation fails.

    OCR and downstream analysis are intentionally handled by the
    background processing pipeline.
    """

    def __init__(
        self,
        *,
        document_service: DocumentService,
        storage_service: StorageService,
    ) -> None:
        self.documents = document_service
        self.storage = storage_service

    async def upload(
        self,
        *,
        org_id: UUID,
        user_id: UUID | None,
        filename: str,
        content_type: str,
        content: bytes,
        industry: str,
        document_type: DocumentType,
        currency: str,
        source_override: str | None = None,
        external_metadata: dict | None = None,
        allow_duplicate: bool = False,
    ) -> Document:
        """Upload and create a document intake record.

        Args:
            allow_duplicate:
                When False, an existing file hash for the organization
                raises DuplicateDocumentError.

                When True, the same file may be uploaded again and will
                receive a new document ID/storage path.
        """

        if not content:
            raise ValueError("Uploaded file is empty.")

        # Content, not extension or the client-declared MIME type, decides
        # whether this is an accepted document. Oversized and spoofed files
        # are rejected before they reach storage.
        inspection = inspect_upload(
            content=content,
            declared_content_type=content_type,
            filename=filename,
            max_size_mb=settings.max_file_size_mb,
        )

        file_type = inspection.file_type

        scan = get_attachment_scanner().scan(content=content, filename=filename)
        quarantined = not scan.clean

        file_hash = hashlib.sha256(content).hexdigest()

        # Duplicate detection happens before storage so we do not create
        # unnecessary orphaned storage objects.
        if not allow_duplicate:
            duplicate = await self.documents.find_duplicate(
                org_id,
                file_hash,
            )

            if duplicate:
                existing_id = getattr(
                    duplicate,
                    "id",
                    None,
                )

                existing_name = getattr(
                    duplicate,
                    "file_name",
                    None,
                )

                raise DuplicateDocumentError(
                    existing_document_id=existing_id,
                    existing_file_name=existing_name,
                )

        document_id = uuid4()

        safe_name = PurePath(
            filename or "document"
        ).name

        owner_path = (
            str(user_id)
            if user_id
            else "email"
        )

        prefix = f"{QUARANTINE_PREFIX}/{org_id}" if quarantined else str(org_id)

        storage_path = (
            f"{prefix}/"
            f"{owner_path}/"
            f"{document_id}/"
            f"{safe_name}"
        )

        await self.storage.upload_document(
            path=storage_path,
            content=content,
            content_type=inspection.content_type,
        )

        metadata = dict(external_metadata or {})
        warnings: list[str] = []

        if quarantined:
            # The object stays private under the quarantine prefix. The
            # document is visible to operators, but its status and failed
            # pipeline stage prevent it from entering OCR.
            metadata["quarantine"] = {
                "status": scan.status,
                "signature": scan.signature,
                "reason": scan.reason,
            }
            warnings.append(
                "Attachment quarantined: " + (scan.reason or "security policy failed.")
            )

        document = Document(
            id=document_id,
            org_id=org_id,
            created_by=user_id,
            source=(
                DocumentSource(source_override)
                if source_override
                else DocumentSource.MANUAL
            ),
            document_type=document_type,
            industry=industry,
            file_url=storage_path,
            file_name=safe_name,
            file_type=file_type,
            file_size_bytes=len(content),
            file_hash=file_hash,
            currency=currency,
            pipeline_stage=(
                PipelineStage.FAILED if quarantined else PipelineStage.INTAKE
            ),
            status=(
                DocumentStatus.QUARANTINED if quarantined else DocumentStatus.PENDING
            ),
            validation_warnings=warnings,
            retry_count=0,
            is_archived=False,
            external_source_data=metadata,
        )

        try:
            return await self.documents.create_document(
                document,
                allow_duplicate=allow_duplicate,
            )

        except TypeError:
            # Backward compatibility with the current DocumentService
            # while the service is being migrated to accept
            # allow_duplicate.
            #
            # Only use the old signature when allow_duplicate is False.
            if allow_duplicate:
                await self.storage.delete_document(
                    storage_path
                )
                raise

            try:
                return await self.documents.create_document(
                    document,
                )
            except Exception:
                await self.storage.delete_document(
                    storage_path
                )
                raise

        except Exception:
            await self.storage.delete_document(
                storage_path
            )
            raise