"""
============================================================
Extraction Service

Orchestrates document extraction.

Responsibilities
----------------
- Decide text vs image extraction
- Use pdf_extractor
- Call ExtractionEngine

No OpenAI code.
No repositories.
No persistence.
============================================================
"""

from __future__ import annotations

from app.services.extraction.extraction_engine import ExtractionEngine
from app.services.pdf_extractor import extract_text_from_pdf
from app.models.invoice import StructuredDocument


class ExtractionService:
    """
    Coordinates extraction workflow.
    """

    def __init__(
        self,
        engine: ExtractionEngine,
    ):
        self.engine = engine

    async def extract(
        self,
        *,
        file_bytes: bytes,
        mime_type: str,
        industry: str,
    ) -> tuple[str, StructuredDocument]:
        """
        Extract structured data from an uploaded document.

        Returns:
            (raw_text, structured_document)
        """

        # Try digital PDF extraction first
        if mime_type == "application/pdf":

            raw_text, is_digital = extract_text_from_pdf(
                file_bytes,
            )

            if is_digital:

                structured = await self.engine.extract_from_text(
                    raw_text,
                    industry,
                )

                return raw_text, structured

        # Otherwise use Vision
        return await self.engine.extract_from_image(
            file_bytes=file_bytes,
            mime_type=mime_type,
            industry=industry,
        )