"""
============================================================
Document Mapper
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.document import (
    Document,
    PurchaseOrder,
    Invoice,
    InvoiceRawText,
    OCRResult,
    DocumentLineItem,
)

from app.schemas.document import (
    DocumentResponse,
    PurchaseOrderResponse,
    InvoiceResponse,
    InvoiceRawTextResponse,
    OCRResultResponse,
    DocumentLineItemResponse,
)


class DocumentMapper(
    BaseMapper[
        Document,
        DocumentResponse,
    ]
):
    domain_model = Document
    response_model = DocumentResponse


class PurchaseOrderMapper(
    BaseMapper[
        PurchaseOrder,
        PurchaseOrderResponse,
    ]
):
    domain_model = PurchaseOrder
    response_model = PurchaseOrderResponse


class InvoiceMapper(
    BaseMapper[
        Invoice,
        InvoiceResponse,
    ]
):
    domain_model = Invoice
    response_model = InvoiceResponse


class InvoiceRawTextMapper(
    BaseMapper[
        InvoiceRawText,
        InvoiceRawTextResponse,
    ]
):
    domain_model = InvoiceRawText
    response_model = InvoiceRawTextResponse


class OCRResultMapper(
    BaseMapper[
        OCRResult,
        OCRResultResponse,
    ]
):
    """
    Maps OCR domain objects to database payloads.

    Used exclusively by OCRResultRepository.
    """

    domain_model = OCRResult
    response_model = OCRResultResponse

    @staticmethod
    def to_insert(
        result: OCRResult,
    ) -> dict:

        return {
            "document_id": str(result.document_id),
            "org_id": str(result.org_id),
            "raw_text": result.raw_text,
            "page_count": result.page_count,
            "pages": result.pages,
            "tables_detected": result.tables_detected,
            "key_value_pairs": result.key_value_pairs,
            "language_detected": result.language_detected,
            "is_handwritten": result.is_handwritten,
            "is_scanned": result.is_scanned,
            "has_tables": result.has_tables,
            "has_signatures": result.has_signatures,
            "image_quality": result.image_quality,
            "engine": result.engine.value,
            "engine_version": result.engine_version,
            "confidence_score": str(result.confidence_score),
            "processing_ms": result.processing_ms,
            "tokens_used": result.tokens_used,
        }

    @staticmethod
    def to_update(
        result: OCRResult,
    ) -> dict:

        payload = OCRResultMapper.to_insert(result)

        payload.pop("document_id", None)
        payload.pop("org_id", None)

        return payload


class DocumentLineItemMapper(
    BaseMapper[
        DocumentLineItem,
        DocumentLineItemResponse,
    ]
):
    domain_model = DocumentLineItem
    response_model = DocumentLineItemResponse