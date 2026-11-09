"""
============================================================
Document Mapper
============================================================

Maps PostgreSQL/Supabase document rows into the application's
Document domain model.

The database contains additional AP, ERP, classification and
sync fields that are intentionally not part of the core
Document domain model.

Canonical accounting database fields:

    amount_paid
    amount_due

Domain compatibility fields:

    paid_amount
    balance_due

The mapper is responsible for translating between those names.
============================================================
"""

from __future__ import annotations

from typing import Any

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

    # =========================================================
    # Database -> Domain
    # =========================================================

    @classmethod
    def to_domain(
        cls,
        row: dict[str, Any] | None,
    ) -> Document | None:
        """
        Convert a documents table row into the Document domain model.

        The documents table contains additional fields used by:

        - AP automation
        - ERP synchronization
        - document classification
        - workflow routing
        - payment processing
        - external integrations

        Those fields are not all part of the core Document model,
        so they must not be passed blindly into Pydantic.
        """

        if row is None:
            return None

        payload = dict(row)

        # -----------------------------------------------------
        # Canonical accounting field mapping
        # -----------------------------------------------------
        #
        # Database:
        #     amount_paid
        #     amount_due
        #
        # Domain:
        #     paid_amount
        #     balance_due
        #
        # The database remains the financial source of truth.
        #

        if "amount_paid" in payload:
            payload["paid_amount"] = payload["amount_paid"]

        if "amount_due" in payload:
            payload["balance_due"] = payload["amount_due"]

        # -----------------------------------------------------
        # Derived payment status
        # -----------------------------------------------------

        if "payment_status" not in payload:
            paid = payload.get("paid_amount")
            balance = payload.get("balance_due")
            total = payload.get("total_amount")

            try:
                paid_value = float(paid or 0)
                balance_value = (
                    float(balance)
                    if balance is not None
                    else None
                )
                total_value = float(total or 0)

                if (
                    balance_value is not None
                    and balance_value <= 0
                    and (total_value > 0 or paid_value > 0)
                ):
                    payload["payment_status"] = "paid"

                elif paid_value > 0:
                    payload["payment_status"] = "partially_paid"

                else:
                    payload["payment_status"] = "unpaid"

            except (TypeError, ValueError):
                payload["payment_status"] = "unpaid"

        # -----------------------------------------------------
        # Keep only fields understood by the domain model.
        # -----------------------------------------------------
        #
        # This is important because documents uses SELECT("*")
        # and the database now contains AP/ERP/classification
        # columns that are not represented by Document.
        #

        allowed_fields = set(
            cls.domain_model.model_fields.keys()
        )

        payload = {
            key: value
            for key, value in payload.items()
            if key in allowed_fields
        }

        return cls.domain_model.model_validate(payload)

    # =========================================================
    # Domain -> Database
    # =========================================================

    @staticmethod
    def to_insert(
        document: Document,
    ) -> dict[str, Any]:
        """
        Convert the Document domain model into a database payload.

        Financial fields are translated back to the canonical
        database column names.
        """

        payload = document.model_dump(
            mode="python",
            exclude_none=True,
        )

        # Domain -> canonical database names
        if "paid_amount" in payload:
            payload["amount_paid"] = payload.pop(
                "paid_amount"
            )

        if "balance_due" in payload:
            payload["amount_due"] = payload.pop(
                "balance_due"
            )

        # payment_status is derived and is not a separate
        # financial source of truth.
        payload.pop(
            "payment_status",
            None,
        )

        return BaseMapper.to_insert(payload)

    @staticmethod
    def to_update(
        document: Document | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert a Document domain model into an update payload.

        Uses canonical database accounting column names.
        """

        if isinstance(document, dict):
            payload = dict(document)
        else:
            payload = document.model_dump(
                mode="python",
                exclude_none=True,
                exclude_unset=True,
            )

        if "paid_amount" in payload:
            payload["amount_paid"] = payload.pop(
                "paid_amount"
            )

        if "balance_due" in payload:
            payload["amount_due"] = payload.pop(
                "balance_due"
            )

        payload.pop(
            "payment_status",
            None,
        )

        return BaseMapper.to_update(payload)


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
            "engine": (
                result.engine.value
                if hasattr(result.engine, "value")
                else str(result.engine)
            ),
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