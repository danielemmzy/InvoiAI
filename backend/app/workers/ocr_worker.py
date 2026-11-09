from __future__ import annotations

import logging
from uuid import UUID

from app.repositories.document.document_repository import (
    DocumentRepository,
)
from app.core.observability import record_extraction
from app.core.error_handler import classify_exception, safe_user_message

from app.services.ocr.ocr_service import (
    OCRService,
)

from app.workers.base import (
    BaseWorker,
)


logger = logging.getLogger(__name__)


class OCRWorker(BaseWorker):
    """
    Background OCR worker.

    The worker delegates document processing to OCRService.

    OCRService is responsible for:
    - document state
    - OCR
    - classification
    - failure persistence

    This worker is responsible for:
    - retrying
    - logging
    - batch pending processing
    """

    name = "ocr-worker"

    def __init__(
        self,
        *,
        ocr_service: OCRService,
        document_repository: DocumentRepository | None = None,
    ) -> None:

        super().__init__()

        self.ocr_service = (
            ocr_service
        )

        self.documents = (
            document_repository
            or DocumentRepository()
        )

    async def run(
        self,
        *,
        document_id: UUID,
        mode: str = "intelligence",
    ) -> None:

        logger.info(
            "OCRWorker processing document: "
            "document_id=%s",
            document_id,
        )

        try:

            await (
                self.ocr_service.run_ocr(
                    document_id=document_id,
                    trigger_analysis=(mode == "intelligence"),
                )
            )

        except Exception as exc:
            record_extraction(result="failed")

            descriptor = classify_exception(exc)
            logger.error(
                "OCRWorker document failed: code=%s service=%s retryable=%s",
                descriptor.code,
                descriptor.service,
                descriptor.retryable,
            )

            if not descriptor.retryable or getattr(self, "_current_attempt", self.retries) >= self.retries:
                try:
                    message = safe_user_message(exc)
                    await self.documents.update_processing_state(
                        document_id,
                        step="failed",
                        message=message,
                        progress=100,
                    )
                    await self.documents.update(
                        document_id,
                        {
                            "status": "failed",
                            "error_message": message,
                        },
                    )
                except Exception:
                    logger.exception(
                        "Could not persist OCR failure state for %s",
                        document_id,
                    )

            raise

        record_extraction(result="success")
        logger.info(
            "OCRWorker document completed: "
            "document_id=%s",
            document_id,
        )

    async def run_pending(
        self,
        *,
        limit: int = 50,
    ) -> dict[str, int]:

        documents = (
            await self.documents
            .list_pending_ocr(
                limit=limit
            )
        )

        processed = 0
        failed = 0

        logger.info(
            "OCRWorker pending scan: "
            "found=%s limit=%s",
            len(documents),
            limit,
        )

        for document in documents:

            try:

                await self.execute(
                    document_id=document.id,
                )

                processed += 1

            except Exception as exc:

                failed += 1

                logger.error(
                    "OCRWorker pending document failed: error_type=%s",
                    type(exc).__name__,
                )

        logger.info(
            "OCRWorker pending scan complete: "
            "processed=%s failed=%s",
            processed,
            failed,
        )

        return {
            "processed": processed,
            "failed": failed,
        }
