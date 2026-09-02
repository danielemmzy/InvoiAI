from __future__ import annotations

from uuid import UUID

from app.models.domain.document import Document
from app.repositories.document.document_repository import DocumentRepository


class DocumentSyncService:
    """
    Synchronizes external documents into InvoiAI.

    Responsibilities
    ----------------
    • Persist external documents
    • Handle external-id upserts
    • Hide repository implementation

    No HTTP.

    No OAuth.

    No provider-specific logic.
    """

    def __init__(self):

        self.repository = DocumentRepository()

    async def sync(
        self,
        *,
        document: Document,
    ) -> Document:

        return await self.repository.upsert_external(
            document,
        )

    async def get_external(
        self,
        *,
        org_id: UUID,
        provider,
        external_id: str,
    ) -> Document | None:

        return await self.repository.get_by_external_id(
            org_id=org_id,
            provider=provider,
            external_id=external_id,
        )