from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.models.invoice import StructuredDocument
from app.services.extraction.extraction_engine import ExtractionEngine


class ExtractionService:
    """Coordinate structured extraction and OCR-to-source verification."""

    def __init__(self, engine: ExtractionEngine):
        self.engine = engine

    async def extract(
        self,
        *,
        file_bytes: bytes,
        mime_type: str,
        industry: str,
        raw_text: str | None = None,
    ) -> tuple[str, StructuredDocument]:
        """
        Structure the text returned by the OCR provider.

        OCR remains the primary owner of document-to-text conversion. When OCR
        text is available, it is always preferred so extraction operates on
        the exact text captured by the OCR stage.

        For image documents, the source bytes are preserved as the fallback
        input if OCR returned no text.

        PDFs fail closed when OCR produced no text because this service does
        not own PDF text extraction.
        """
        text = (raw_text or "").strip()

        if text:
            structured = await self.engine.extract_from_text(
                text,
                industry,
            )
            return text, structured

        if mime_type == "application/pdf":
            raise ValueError(
                "OCR returned no text for the PDF; refusing to continue with empty financial data."
            )

        if not file_bytes:
            raise ValueError(
                "OCR returned no text and the source document bytes are unavailable."
            )

        extracted_text, structured = await self.engine.extract_from_image(
            file_bytes=file_bytes,
            mime_type=mime_type,
            industry=industry,
        )

        return extracted_text, structured

    async def compare_ocr_to_image(
        self,
        *,
        file_bytes: bytes,
        mime_type: str,
        industry: str,
        structured_from_ocr: StructuredDocument,
    ) -> list[str]:
        """
        Independently extract an image document and compare its financial
        fields with the OCR-derived structured document.

        PDF comparison is skipped because the current ExtractionEngine exposes
        image extraction, not PDF-page rendering.
        """
        if not file_bytes:
            return [
                "OCR-to-image verification could not be performed because the source document bytes are unavailable."
            ]

        if mime_type == "application/pdf":
            return []

        try:
            _, structured_from_image = await self.engine.extract_from_image(
                file_bytes=file_bytes,
                mime_type=mime_type,
                industry=industry,
            )
        except Exception as exc:
            return [
                "OCR-to-image verification failed: "
                f"{type(exc).__name__}: {exc}"
            ]

        return self._compare_structured_documents(
            structured_from_ocr,
            structured_from_image,
        )

    @classmethod
    def _compare_structured_documents(
        cls,
        ocr_document: StructuredDocument,
        image_document: StructuredDocument,
    ) -> list[str]:
        warnings: list[str] = []

        fields = (
            ("vendor_name", "vendor name"),
            ("document_number", "document number"),
            ("document_date", "document date"),
            ("due_date", "due date"),
            ("currency", "currency"),
            ("subtotal", "subtotal"),
            ("tax_rate", "tax rate"),
            ("tax_amount", "tax amount"),
            ("total_amount", "total amount"),
            ("amount_due", "amount due"),
        )

        for field_name, label in fields:
            ocr_value = getattr(ocr_document, field_name, None)
            image_value = getattr(image_document, field_name, None)
            if ocr_value is None:
                ocr_value = (getattr(ocr_document, "raw_totals", None) or {}).get(field_name)
            if image_value is None:
                image_value = (getattr(image_document, "raw_totals", None) or {}).get(field_name)

            if ocr_value in (None, "") and image_value in (None, ""):
                continue

            if not cls._values_match(ocr_value, image_value):
                warnings.append(
                    f"OCR/image disagreement for {label}: "
                    f"OCR extracted {ocr_value!r}, "
                    f"image extraction returned {image_value!r}."
                )

        return warnings

    @staticmethod
    def _values_match(
        left: object,
        right: object,
    ) -> bool:
        if left is None or right is None:
            return left is right

        if isinstance(left, str) and isinstance(right, str):
            return (
                " ".join(left.split()).strip().casefold()
                == " ".join(right.split()).strip().casefold()
            )

        try:
            left_decimal = Decimal(
                str(left).replace(",", "").strip()
            )
            right_decimal = Decimal(
                str(right).replace(",", "").strip()
            )
            return left_decimal == right_decimal
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            return (
                str(left).strip().casefold()
                == str(right).strip().casefold()
            )
