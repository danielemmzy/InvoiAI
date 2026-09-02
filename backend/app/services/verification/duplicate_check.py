"""
============================================================
Duplicate Check Module

Verification Module 4

Responsibilities
----------------
- Detect duplicate documents
- Detect repeated invoice numbers
- Detect duplicate file hashes
- Detect suspicious repeated invoices

No database.
No repositories.

Repository/service layer provides comparison documents.
============================================================
"""

from __future__ import annotations

from app.models.domain.document import Document
from app.services.verification.result import VerificationResult


class DuplicateCheck:
    """
    Duplicate document validation.
    """

    def __init__(self):
        pass


    async def run(
        self,
        document: Document,
        duplicate_document: Document | None,
    ) -> VerificationResult:
        """
        Compare document against previous documents.

        duplicate_document is provided by repository/service layer.
        """

        passed = True

        score = 100

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        metadata: dict = {}


        # =====================================================
        # No duplicate found
        # =====================================================

        if duplicate_document is None:

            positives.append(
                "No duplicate document detected."
            )

            return VerificationResult(
                passed=True,
                score=100,
                confidence=100,
                summary="Duplicate validation completed.",
                reasons=reasons,
                positives=positives,
                warnings=warnings,
                metadata={
                    "duplicate_found": False,
                },
            )


        # =====================================================
        # File Hash Match
        # =====================================================

        if (
            document.file_hash
            and duplicate_document.file_hash
            and document.file_hash == duplicate_document.file_hash
        ):

            passed = False

            score -= 70

            reasons.append(
                "Document file hash matches previous document."
            )

            metadata["hash_match"] = True



        # =====================================================
        # Invoice Number Match
        # =====================================================

        if (
            document.document_number
            and duplicate_document.document_number
            and (
                document.document_number
                ==
                duplicate_document.document_number
            )
        ):

            passed = False

            score -= 40

            reasons.append(
                "Document number already exists."
            )

            metadata["document_number_match"] = True



        # =====================================================
        # Vendor + Amount Pattern
        # =====================================================

        if (
            document.vendor_id
            and duplicate_document.vendor_id
            and document.vendor_id == duplicate_document.vendor_id
            and document.total_amount
            and duplicate_document.total_amount
            and (
                document.total_amount
                ==
                duplicate_document.total_amount
            )
        ):

            warnings.append(
                "Same vendor and amount found in previous document."
            )

            score -= 20

            metadata["amount_pattern_match"] = True



        metadata.update(
            {
                "duplicate_found": True,
                "duplicate_document_id":
                    duplicate_document.id,
            }
        )


        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=100,
            summary="Duplicate validation completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata=metadata,
        )