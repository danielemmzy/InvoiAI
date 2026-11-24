from __future__ import annotations

from uuid import UUID

from app.mappers.document_mapper import OCRResultMapper
from app.models.domain.document import OCRResult
from app.repositories.base import BaseRepository
from app.core.db import execute


class OCRRepository(BaseRepository):
    """
    Repository responsible for OCR result persistence.

    Responsibilities
    ----------------
    - Create OCR results
    - Retrieve OCR results
    - Retrieve the latest OCR result for a document

    No business logic belongs here.
    """

    table_name = "ocr_results"
    mapper = OCRResultMapper

    # =========================================================
    # Creation
    # =========================================================

    async def create_ocr_result(
        self,
        result: OCRResult,
    ) -> OCRResult:
        """
        Persist an OCR result.
        """

        return await self.create(
            result
        )

    # =========================================================
    # Retrieval
    # =========================================================

    async def get_ocr_result(
        self,
        ocr_result_id: UUID,
    ) -> OCRResult | None:
        """
        Retrieve an OCR result by ID.
        """

        return await self.get(
            ocr_result_id
        )

    async def get_latest_for_document(
        self,
        document_id: UUID,
    ) -> OCRResult | None:
        """
        Retrieve the latest OCR result for a document.
        """

        response = await execute(
            self.table()
            .select("*")
            .eq(
                "document_id",
                str(document_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(1)
        )

        return self._one(
            response
        )

    async def list_for_document(
        self,
        document_id: UUID,
        *,
        limit: int = 50,
    ) -> list[OCRResult]:
        """
        List OCR results for a document.
        """

        response = await execute(
            self.table()
            .select("*")
            .eq(
                "document_id",
                str(document_id),
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
        )

        return self._many(
            response
        )
