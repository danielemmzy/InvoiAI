from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.core.enum.database import (
    DocumentStatus,
    RecommendationType,
    DocumentType,
    PipelineStage,
)

from app.repositories.document.analysis_repository import (
    AnalysisRepository,
)
from app.repositories.document.document_repository import (
    DocumentRepository,
)
from app.repositories.document.ocr_repository import (
    OCRRepository,
)
from app.repositories.document.purchase_order_repository import (
    PurchaseOrderRepository,
)

from app.services.analysis.analysis_builder import (
    AnalysisBuilder,
)
from app.services.validation_service import (
    ValidationService,
)
from app.services.verification.engine import (
    VerificationEngine,
)

from app.workers.embedding_worker import (
    EmbeddingWorker,
)


logger = logging.getLogger(__name__)


class AnalysisService:
    """
    AI Analysis orchestration service.

    Responsibilities
    ----------------
    • Load document
    • Load OCR
    • Load supporting data
    • Execute verification engine
    • Build analysis
    • Persist analysis
    • Update document status
    • Trigger embedding worker

    No SQL.
    No AI logic.
    """

    def __init__(
        self,
        *,
        repository: AnalysisRepository,
        document_repository: DocumentRepository,
        ocr_repository: OCRRepository,
        purchase_order_repository: PurchaseOrderRepository,
        verification_engine: VerificationEngine,
        embedding_worker: EmbeddingWorker,
        validation_service: ValidationService | None = None,
    ) -> None:

        self.repository = repository
        self.document_repository = document_repository
        self.ocr_repository = ocr_repository
        self.purchase_order_repository = purchase_order_repository
        self.verification_engine = verification_engine
        self.embedding_worker = embedding_worker
        self.validation_service = validation_service or ValidationService()

    async def _progress(
        self,
        document_id: UUID,
        step: str,
        message: str,
        progress: int,
    ) -> None:
        await self.document_repository.update_processing_state(
            document_id,
            step=step,
            message=message,
            progress=progress,
        )

    # =====================================================
    # Analysis
    # =====================================================

    async def analyze_document(
        self,
        *,
        document_id: UUID,
    ):

        document = await self.document_repository.get_document(
            document_id,
        )

        if document is None:
            raise ValueError(
                "Document not found.",
            )

        await self.document_repository.update_document_status(
            document.id,
            DocumentStatus.ANALYSIS_RUNNING,
        )
        await self._progress(
            document.id,
            "analysis",
            "Reading the extracted data and preparing financial checks",
            44,
        )

        ocr = await self.ocr_repository.get_latest_for_document(
            document.id,
        )

        if ocr is None:
            raise ValueError(
                "OCR result not found.",
            )

        line_items = await self.document_repository.get_document_line_items(
            document.id,
        )

        # Business validation (field/date/amount/math checks) runs
        # before the 8-module verification engine, matching Flow 3.
        # Warnings never block the pipeline; hard errors are surfaced
        # via analysis.module_results so a human can see them on review.
        await self._progress(
            document.id,
            "validation",
            "Checking dates, amounts, totals, and financial consistency",
            50,
        )
        validation = await self.validation_service.validate(
            document,
            line_items,
        )

        vendor = (
            await self.document_repository.get_vendor(
                document.vendor_id,
            )
            if document.vendor_id
            else None
        )

        purchase_order = (
            await self.purchase_order_repository.get_purchase_order(
                document.purchase_order_id,
            )
            if document.purchase_order_id
            else None
        )

        duplicate_document = (
            await self.document_repository.get_document_by_hash(
                document.org_id,
                document.file_hash,
                exclude_document_id=document.id,
            )
            if document.file_hash
            else None
        )

        verification = await self.verification_engine.verify(
            document=document,
            ocr=ocr,
            line_items=line_items,
            vendor=vendor,
            purchase_order=purchase_order,
            duplicate_document=duplicate_document,
            progress_callback=lambda step, message, progress: self._progress(
                document.id, step, message, progress
            ),
        )

        analysis = AnalysisBuilder.build(
            document=document,
            ocr=ocr,
            verification=verification,
        )

        payload = analysis.model_dump(
            mode="json",
        )

        # Surface validation warnings/errors alongside the module
        # results so a reviewer sees both without a second query.
        payload.setdefault("module_results", {})
        if isinstance(payload["module_results"], dict):
            payload["module_results"]["validation"] = {
                "passed": validation.passed,
                "warnings": validation.warnings,
                "errors": validation.errors,
            }

        await self.repository.create_analysis(
            payload,
        )

        if validation.warnings:
            # Persist validation_warnings on the document row directly
            # (documents.validation_warnings), matching Flow 3.
            await self.document_repository.update(
                document.id,
                {"validation_warnings": validation.warnings},
            )

        status = (
            DocumentStatus.APPROVED
            if analysis.recommendation
            == RecommendationType.APPROVE
            else DocumentStatus.REJECTED
            if analysis.recommendation
            == RecommendationType.REJECT
            else DocumentStatus.NEEDS_REVIEW
        )

        await self.document_repository.update_document_status(
            document.id,
            status,
        )
        await self._progress(
            document.id,
            "embedding",
            "Building financial memory so InvoiAI can search and understand this document later",
            94,
        )

        # AP automation is additive: only invoice documents that were not
        # rejected enter the new AP control plane. Existing OCR/verification
        # and embedding behaviour remains unchanged.
        if document.document_type == DocumentType.RECEIPT and status != DocumentStatus.REJECTED:
            if document.total_amount and document.total_amount > 0:
                from app.core.enum.finance import OwnerType
                from app.services.finance.expense_service import ExpenseService
                await ExpenseService().create(owner_type=OwnerType.ORGANIZATION, owner_id=document.org_id, amount=document.total_amount, description=document.vendor_name or document.file_name, expense_date=document.document_date, document_id=document.id)
            from app.core.supabase import get_supabase
            get_supabase().table("documents").update({"workflow_route":"business_expense"}).eq("id",str(document.id)).execute()

        task = asyncio.create_task(
            self.embedding_worker.execute(document_id=document.id),
            name=f"embedding:{document.id}",
        )
        task.add_done_callback(self._log_embedding_failure)

        return analysis

    @staticmethod
    def _log_embedding_failure(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        try:
            task.result()
        except Exception:
            logger.exception("Background embedding task failed")


    # =====================================================
    # Retrieval
    # =====================================================

    async def get_analysis(
        self,
        *,
        analysis_id: UUID,
    ):

        analysis = await self.repository.get_analysis(
            str(analysis_id),
        )

        if analysis is None:
            raise ValueError(
                "Analysis not found.",
            )

        return analysis

    async def get_document_analysis(
        self,
        *,
        document_id: UUID,
    ):

        analysis = await self.repository.get_document_analysis(
            str(document_id),
        )

        if analysis is None:
            raise ValueError(
                "Analysis not found.",
            )

        return analysis

    async def list_document_analyses(
        self,
        *,
        document_id: UUID,
    ):

        return await self.repository.list_document_analyses(
            str(document_id),
        )

    async def list_organization_analyses(
        self,
        *,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ):

        return await self.repository.list_organization_analyses(
            org_id,
            limit,
            offset,
        )

    # =====================================================
    # Human Review
    # =====================================================

    async def submit_review(
        self,
        *,
        analysis_id: UUID,
        reviewer_id: UUID,
        decision: RecommendationType,
        override_reason: str | None = None,
    ):

        analysis = await self.repository.get_analysis(
            str(analysis_id),
        )

        if analysis is None:
            raise ValueError(
                "Analysis not found.",
            )

        return await self.repository.submit_review(
            str(analysis_id),
            str(reviewer_id),
            decision,
            override_reason,
        )

    async def clear_review(
        self,
        *,
        analysis_id: UUID,
    ):

        analysis = await self.repository.get_analysis(
            str(analysis_id),
        )

        if analysis is None:
            raise ValueError(
                "Analysis not found.",
            )

        return await self.repository.clear_review(
            str(analysis_id),
        )

    # =====================================================
    # Statistics
    # =====================================================

    async def count_analyses(
        self,
        *,
        org_id: UUID,
    ):

        return await self.repository.count_analyses(
            str(org_id),
        )

    async def health_scores(
        self,
        *,
        org_id: UUID,
    ):

        return await self.repository.get_health_scores(
            str(org_id),
        )

    async def risk_distribution(
        self,
        *,
        org_id: UUID,
    ):

        return await self.repository.risk_distribution(
            str(org_id),
        )

    async def recommendation_distribution(
        self,
        *,
        org_id: UUID,
    ):

        return await self.repository.recommendation_distribution(
            str(org_id),
        )

    # =====================================================
    # Helpers
    # =====================================================

    async def analysis_exists(
        self,
        *,
        document_id: UUID,
    ) -> bool:

        return await self.repository.analysis_exists(
            str(document_id),
        )

    async def latest_analysis_id(
        self,
        *,
        document_id: UUID,
    ):

        return await self.repository.latest_analysis_id(
            str(document_id),
        )

    async def latest_analysis_version(
        self,
        *,
        document_id: UUID,
    ):

        return await self.repository.latest_analysis_version(
            str(document_id),
        )

    async def has_human_review(
        self,
        *,
        analysis_id: UUID,
    ) -> bool:

        return await self.repository.has_human_review(
            str(analysis_id),
        )