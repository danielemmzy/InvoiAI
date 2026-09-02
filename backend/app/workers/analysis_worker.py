from __future__ import annotations

import logging
from uuid import UUID

from app.services.analysis.analysis_service import AnalysisService
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

        await self.analysis_service.analyze_document(
            document_id=document_id,
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
