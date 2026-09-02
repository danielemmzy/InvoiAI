from __future__ import annotations

import hashlib
from pathlib import PurePath
from uuid import UUID, uuid4

from app.core.enum.database import DocumentSource, DocumentStatus, DocumentType, FileType, PipelineStage
from app.models.domain.document import Document
from app.services.document.document_service import DocumentService
from app.services.storage.storage import StorageService


class DocumentUploadService:
    """Application service for V2 document intake.

    Owns file validation, content hashing, durable storage, duplicate
    detection and creation of the initial document record. OCR/analysis
    are intentionally left to the background pipeline.
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
    ) -> Document:
        if not content:
            raise ValueError("Uploaded file is empty.")

        file_type = self._file_type(content_type, filename)
        file_hash = hashlib.sha256(content).hexdigest()

        duplicate = await self.documents.find_duplicate(
            org_id,
            file_hash,
        )
        if duplicate:
            raise ValueError("A document with the same file already exists.")

        document_id = uuid4()
        safe_name = PurePath(filename).name
        owner_path = str(user_id) if user_id else "email"
        storage_path = f"{org_id}/{owner_path}/{document_id}/{safe_name}"

        await self.storage.upload_document(
            path=storage_path,
            content=content,
            content_type=content_type,
        )

        document = Document(
            id=document_id,
            org_id=org_id,
            created_by=user_id,
            source=DocumentSource(source_override) if source_override else DocumentSource.MANUAL,
            document_type=document_type,
            industry=industry,
            file_url=storage_path,
            file_name=safe_name,
            file_type=file_type,
            file_size_bytes=len(content),
            file_hash=file_hash,
            currency=currency,
            pipeline_stage=PipelineStage.INTAKE,
            status=DocumentStatus.PENDING,
            validation_warnings=[],
            retry_count=0,
            is_archived=False,
            external_source_data=external_metadata or {},
        )

        try:
            return await self.documents.create_document(document)
        except Exception:
            await self.storage.delete_document(storage_path)
            raise

    @staticmethod
    def _file_type(content_type: str, filename: str) -> FileType:
        extension = PurePath(filename).suffix.lower().lstrip(".")
        aliases = {"jpeg": "jpeg", "jpg": "jpg", "png": "png", "webp": "webp", "pdf": "pdf"}
        value = aliases.get(extension)
        if value is None:
            mime_map = {
                "application/pdf": "pdf",
                "image/jpeg": "jpeg",
                "image/png": "png",
                "image/webp": "webp",
            }
            value = mime_map.get(content_type)
        if value is None:
            raise ValueError("Unsupported document file type.")
        return FileType(value)
