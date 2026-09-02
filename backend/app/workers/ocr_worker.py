from __future__ import annotations

import logging
from uuid import UUID

from app.services.ocr.ocr_service import OCRService
from app.repositories.document.document_repository import DocumentRepository
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class OCRWorker(BaseWorker):
    """
    Background OCR worker.

    Loads no repositories.

    Delegates everything to OCRService.
    """

    name = "ocr-worker"

    def __init__(
        self,
        *,
        ocr_service: OCRService,
        document_repository: DocumentRepository | None = None,
    ) -> None:

        super().__init__()

        self.ocr_service = ocr_service
        self.documents = document_repository or DocumentRepository()

    async def run(
        self,
        *,
        document_id: UUID,
    ) -> None:

        logger.info(
            "Starting OCR for document %s",
            document_id,
        )

        await self.ocr_service.run_ocr(
            document_id=document_id,
        )

        logger.info(
            "OCR completed for document %s",
            document_id,
        )

    async def run_pending(self, *, limit: int = 50) -> dict[str, int]:
        documents = await self.documents.list_pending_ocr(limit=limit)
        processed = 0
        failed = 0
        for document in documents:
            try:
                await self.execute(document_id=document.id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("OCR failed for document %s", document.id)
        return {"processed": processed, "failed": failed}
