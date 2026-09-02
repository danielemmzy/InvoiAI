"""
============================================================
Document Context

Runtime document context.

Carries the current document through the
processing pipeline.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel

from app.core.enum.database import DocumentStatus, DocumentType


class DocumentContext(BaseModel):
    """
    Current document.
    """

    document_id: UUID

    org_id: UUID

    document_type: DocumentType

    status: DocumentStatus

    vendor_id: UUID | None = None

    analysis_id: UUID | None = None

    workflow_id: UUID | None = None

    file_name: str

    file_url: str

    request_id: str | None = None