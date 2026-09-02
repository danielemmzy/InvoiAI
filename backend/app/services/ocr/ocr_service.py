from __future__ import annotations

import time
from decimal import Decimal
from uuid import UUID
from datetime import UTC, datetime

from app.core.enum.database import (
    OCREngineType,
    PipelineStage,
)

from app.integrations.google.google_document_ai_service import (
    GoogleDocumentAIService,
)

from app.models.domain.document import OCRResult

from app.repositories.document.document_repository import (
    DocumentRepository,
)

from app.services.storage.storage import (
    StorageService,
)

from app.workers.analysis_worker import (
    AnalysisWorker,
)
from app.services.document.classifier_service import DocumentClassifierService
from app.services.document.workflow_router import route_for
from app.services.extraction.personal_extractor import PersonalExtractor
from app.core.enum.finance import OwnerType
from app.core.supabase import get_supabase


class OCRService:
    """
    OCR orchestration service.

    Responsibilities
    ----------------
    • Load document
    • Download file
    • Execute Google Document AI
    • Persist OCR result
    • Update pipeline
    • Trigger Analysis

    No SQL.
    """

    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        storage_service: StorageService,
        provider: GoogleDocumentAIService,
        analysis_worker: AnalysisWorker,
        classifier: DocumentClassifierService | None = None,
    ) -> None:

        self.document_repository = document_repository
        self.storage = storage_service
        self.provider = provider
        self.analysis_worker = analysis_worker
        self.classifier = classifier or DocumentClassifierService()

    # =====================================================
    # OCR
    # =====================================================

    async def run_ocr(
        self,
        *,
        document_id: UUID,
    ) -> OCRResult:

        document = await self.document_repository.get_document(
            document_id,
        )

        if document is None:
            raise ValueError("Document not found.")

        await self.document_repository.update_pipeline_stage(
            document.id,
            PipelineStage.OCR,
        )

        file_bytes = await self.storage.download_document(
            document.file_url,
        )

        started = time.perf_counter()

        google_document = self.provider.process_document(
            content=file_bytes,
            mime_type=document.file_type.value,
        )

        processing_ms = int(
            (time.perf_counter() - started) * 1000
        )

        raw_text = google_document.text or ""

        pages = []

        for index, page in enumerate(google_document.pages):

            page_text = ""

            if page.layout.text_anchor.text_segments:

                for segment in page.layout.text_anchor.text_segments:

                    start = int(segment.start_index or 0)
                    end = int(segment.end_index)

                    page_text += raw_text[start:end]

            pages.append(
                {
                    "page_number": index + 1,
                    "text": page_text,
                }
            )

        tables = []

        for page in google_document.pages:

            for table in page.tables:

                tables.append(
                    {
                        "header_rows": len(table.header_rows),
                        "body_rows": len(table.body_rows),
                    }
                )

        languages = set()

        for page in google_document.pages:

            for lang in page.detected_languages:

                languages.add(lang.language_code)

        confidences = []

        for page in google_document.pages:

            if page.layout.confidence is not None:
                confidences.append(page.layout.confidence)

        confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else 0
        )

        result = OCRResult(
            document_id=document.id,
            org_id=document.org_id,
            raw_text=raw_text,
            page_count=len(google_document.pages),
            pages=pages,
            tables_detected=tables,
            key_value_pairs={},
            language_detected=",".join(sorted(languages)) if languages else None,
            is_handwritten=False,
            is_scanned=document.file_type.value == "application/pdf",
            has_tables=len(tables) > 0,
            has_signatures=False,
            image_quality=100,
            engine=OCREngineType.GOOGLE_DOCUMENT_AI,
            engine_version=None,
            confidence_score=Decimal(str(round(confidence, 4))),
            processing_ms=processing_ms,
            tokens_used=0,
        )

        await self.document_repository.create_ocr_result(result)
        classification=await self.classifier.classify(result.raw_text,document.file_name)
        from app.core.enum.database import DocumentType
        detected=classification["document_type"]
        if document.document_type==DocumentType.UNKNOWN or document.source.value=="manual":
            await self.document_repository.update(document.id,{"document_type":detected,"classification_confidence":classification["confidence"],"classification_reason":classification["reason"],"workflow_route":route_for(detected),"classified_at":datetime.now(UTC).isoformat()})
            document.document_type=DocumentType(detected)
        else:
            await self.document_repository.update(document.id,{"classification_confidence":classification["confidence"],"classification_reason":classification["reason"],"workflow_route":route_for(document.document_type.value),"classified_at":datetime.now(UTC).isoformat()})
        if document.document_type==DocumentType.BANK_STATEMENT:
            org=get_supabase().table("organizations").select("features").eq("id",str(document.org_id)).single().execute().data or {}
            if (org.get("features") or {}).get("personal_mode") and document.created_by:
                account_id=(document.external_source_data or {}).get("financial_account_id")
                data=await PersonalExtractor().process(owner_type=OwnerType.PERSONAL,owner_id=document.created_by,document_id=document.id,raw_text=result.raw_text,account_id=UUID(str(account_id)) if account_id else None)
                await self.document_repository.update(document.id,{"workflow_route":"personal_finance","status":"approved","external_source_data":{**(document.external_source_data or {}),"statement_import":data}})
                return result
        await self.document_repository.update_pipeline_stage(document.id,PipelineStage.AI_ANALYSIS)
        await self.analysis_worker.execute(document_id=document.id)

        return result

    # =====================================================
    # Reprocess
    # =====================================================

    async def reprocess(
        self,
        *,
        document_id: UUID,
    ) -> OCRResult:

        return await self.run_ocr(
            document_id=document_id,
        )