"""
============================================================
Duplicate Detection Service

Industry-standard duplicate detection for AP automation.

Responsibilities
----------------
- Exact file duplicate detection
- Duplicate invoice number detection
- Vendor + Amount + Date detection
- Near duplicate detection
- Risk scoring
- Duplicate explanation

This service contains BUSINESS LOGIC.

Repositories ONLY retrieve data.

Inspired by:
- SAP Concur
- Coupa
- Oracle AP
- Tipalti
============================================================
"""

from __future__ import annotations

from decimal import Decimal

from app.models.domain.document import Document
from app.repositories.document.document_repository import DocumentRepository
from app.services.verification.result import VerificationResult


class DuplicateService:
    """
    Detect duplicate invoices.

    Priority
    --------
    1. Exact file duplicate
    2. Duplicate invoice number
    3. Vendor + Amount + Date
    4. Historical suspicious invoices
    """

    def __init__(self):

        self.documents = DocumentRepository()

    # =========================================================
    # Public API
    # =========================================================

    async def verify(
        self,
        *,
        document: Document,
    ) -> VerificationResult:

        duplicate = await self.documents.find_duplicate(
            org_id=document.org_id,
            document=document,
        )

        if duplicate is None:

            return VerificationResult(
                passed=True,
                score=100,
                confidence=100,
                summary="No duplicate document detected.",
                reasons=[],
                positives=[
                    "No duplicate invoice found."
                ],
                warnings=[],
                metadata={
                    "duplicate_found": False,
                },
            )

        score = 100

        confidence = 100

        passed = False

        reasons = []

        positives = []

        warnings = []

        metadata = {
            "duplicate_found": True,
            "duplicate_document_id": duplicate.id,
        }

        # =====================================================
        # Exact File Duplicate
        # =====================================================

        if (
            document.file_hash
            and duplicate.file_hash
            and document.file_hash == duplicate.file_hash
        ):

            score -= 70

            reasons.append(
                "Exact file duplicate detected."
            )

            metadata["hash_match"] = True

        # =====================================================
        # Duplicate Invoice Number
        # =====================================================

        if (
            document.document_number
            and duplicate.document_number
            and (
                document.document_number
                == duplicate.document_number
            )
        ):

            score -= 40

            reasons.append(
                "Invoice number already exists."
            )

            metadata["invoice_number_match"] = True

        # =====================================================
        # Vendor + Amount
        # =====================================================

        if (
            document.vendor_id
            and duplicate.vendor_id
            and document.vendor_id == duplicate.vendor_id
            and document.total_amount
            and duplicate.total_amount
            and Decimal(document.total_amount)
            == Decimal(duplicate.total_amount)
        ):

            score -= 20

            warnings.append(
                "Same vendor and invoice amount detected."
            )

            metadata["vendor_amount_match"] = True

        # =====================================================
        # Invoice Date
        # =====================================================

        if (
            document.document_date
            and duplicate.document_date
            and document.document_date
            == duplicate.document_date
        ):

            score -= 10

            warnings.append(
                "Invoice dates are identical."
            )

            metadata["date_match"] = True

        # =====================================================
        # Historical duplicates
        # =====================================================

        history = (
            await self.documents.list_possible_duplicates(
                org_id=document.org_id,
                vendor_id=document.vendor_id,
                amount=document.total_amount,
            )
        )

        if history:

            metadata["similar_documents"] = len(history)

            warnings.append(
                f"{len(history)} similar invoices found."
            )

        score = max(score, 0)

        return VerificationResult(
            passed=passed,
            score=score,
            confidence=confidence,
            summary="Duplicate detection completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata=metadata,
        )

    # =========================================================
    # Quick Duplicate Check
    # =========================================================

    async def is_duplicate(
        self,
        *,
        document: Document,
    ) -> bool:

        duplicate = await self.documents.find_duplicate(
            org_id=document.org_id,
            document=document,
        )

        return duplicate is not None

    # =========================================================
    # Duplicate Details
    # =========================================================

    async def duplicate_document(
        self,
        *,
        document: Document,
    ) -> Document | None:

        return await self.documents.find_duplicate(
            org_id=document.org_id,
            document=document,
        )

    # =========================================================
    # Risk Score Only
    # =========================================================

    async def risk_score(
        self,
        *,
        document: Document,
    ) -> int:

        result = await self.verify(
            document=document,
        )

        return 100 - result.score