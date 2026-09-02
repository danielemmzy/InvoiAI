from __future__ import annotations

import logging
from uuid import UUID

from app.repositories.document.document_repository import (
    DocumentRepository,
)

from app.services.embedding_service import (
    EmbeddingService,
)

from app.workers.base import (
    BaseWorker,
)

logger = logging.getLogger(__name__)


class EmbeddingWorker(BaseWorker):
    """
    Background embedding worker.

    Responsibilities
    ----------------
    • Load document
    • Delegate embedding generation
    • Retry failed jobs

    No embedding logic.
    """

    name = "embedding-worker"

    def __init__(
        self,
        *,
        repository: DocumentRepository,
        embedding_service: EmbeddingService,
    ) -> None:

        super().__init__()

        self.repository = repository
        self.embedding_service = embedding_service

    async def run(
        self,
        *,
        document_id: UUID,
    ) -> None:

        logger.info(
            "Generating embedding for document %s",
            document_id,
        )

        document = await self.repository.get_document(
            document_id,
        )

        if document is None:
            raise ValueError(
                "Document not found."
            )

        await self.embedding_service.document_embedding(
            document,
        )

        logger.info(
            "Embedding generated for document %s",
            document_id,
        )

    async def run_pending(self, *, limit: int = 50) -> dict[str, int]:
        documents = await self.repository.list_documents_for_embedding(limit=limit)
        processed = 0
        skipped = 0
        failed = 0
        for document in documents:
            if document.id is None or await self.embedding_exists(document.id):
                skipped += 1
                continue
            try:
                await self.execute(document_id=document.id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("Embedding failed for document %s", document.id)
        return {"processed": processed, "skipped": skipped, "failed": failed}

    async def embedding_exists(self, document_id: UUID) -> bool:
        return await self.embedding_service.repository.document_embedding_exists(document_id)
