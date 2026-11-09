from __future__ import annotations

import logging
from uuid import UUID

from app.services.analysis.analysis_service import AnalysisService
from app.core.error_handler import classify_exception, safe_user_message
from app.repositories.document.document_repository import DocumentRepository
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class AnalysisWorker(BaseWorker):
    """
    Background Analysis Worker.

    Responsibilities
    ----------------
    • Execute AI analysis asynchronously
    • Keep API requests fast
    • Delegate all work to AnalysisService

    No business logic.
    No repositories.
    """

    name = "analysis-worker"

    def __init__(
        self,
        *,
        analysis_service: AnalysisService,
        document_repository: DocumentRepository | None = None,
    ) -> None:

        super().__init__()

        self.analysis_service = analysis_service
        self.documents = document_repository or DocumentRepository()

    # =====================================================
    # Execute
    # =====================================================

    async def run(
        self,
        *,
        document_id: UUID,
    ) -> None:

        logger.info(
            "Starting analysis for document %s",
            document_id,
        )

        try:
            await self.analysis_service.analyze_document(
                document_id=document_id,
            )
        except Exception as exc:
            descriptor = classify_exception(exc)
            # A failed analysis must become a visible terminal processing
            # state. The user-facing message is centralized so platform
            # failures (AI/database/network) are not exposed as raw traces.
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
                        {"status": "failed", "error_message": message, "intelligence_status": "failed"},
                    )
                except Exception:
                    logger.exception("Could not persist analysis failure state for %s", document_id)
            logger.error(
                "Analysis failed for document %s: code=%s service=%s retryable=%s",
                document_id, descriptor.code, descriptor.service, descriptor.retryable, exc_info=True,
            )
            raise

        await self.documents.update(
            document_id,
            {"intelligence_status": "complete"},
        )
        logger.info(
            "Analysis completed for document %s",
            document_id,
        )

    async def run_pending(self, *, limit: int = 50) -> dict[str, int]:
        documents = await self.documents.list_pending_analysis(limit=limit)
        processed = 0
        failed = 0
        for document in documents:
            try:
                await self.execute(document_id=document.id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("Analysis failed for document %s", document.id)
        return {"processed": processed, "failed": failed}
