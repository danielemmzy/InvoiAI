"""
============================================================
Compliance Check

Verification Module 8

Responsibilities
----------------
- Validate required document fields
- Validate document dates
- Validate monetary fields
- Validate payment information
- Prepare for future policy rules

No database.
No repositories.
============================================================
"""

from __future__ import annotations

from datetime import date

from app.models.domain.document import Document
from app.services.verification.result import VerificationResult


class ComplianceCheck:
    """
    Compliance validation.
    """

    async def run(
        self,
        document: Document,
    ) -> VerificationResult:

        passed = True

        score = 100

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        today = date.today()

        # -----------------------------------------------------
        # Required Fields
        # -----------------------------------------------------

        if not document.vendor_name:

            passed = False

            score -= 20

            reasons.append(
                "Vendor name is missing."
            )

        if not document.document_number:

            passed = False

            score -= 20

            reasons.append(
                "Document number is missing."
            )

        if document.total_amount is None:

            passed = False

            score -= 20

            reasons.append(
                "Total amount is missing."
            )

        # -----------------------------------------------------
        # Document Date
        # -----------------------------------------------------

        if document.document_date is None:

            warnings.append(
                "Document date is missing."
            )

            score -= 5

        elif document.document_date > today:

            passed = False

            score -= 20

            reasons.append(
                "Document date is in the future."
            )

        else:

            positives.append(
                "Document date is valid."
            )

        # -----------------------------------------------------
        # Due Date
        # -----------------------------------------------------

        if (
            document.document_date
            and document.due_date
            and document.due_date < document.document_date
        ):

            warnings.append(
                "Due date occurs before document date."
            )

            score -= 10

        # -----------------------------------------------------
        # Currency
        # -----------------------------------------------------

        if document.currency:

            positives.append(
                "Currency specified."
            )

        else:

            warnings.append(
                "Currency missing."
            )

            score -= 10

        # -----------------------------------------------------
        # Payment Terms
        # -----------------------------------------------------

        if document.payment_terms:

            positives.append(
                "Payment terms present."
            )

        else:

            warnings.append(
                "Payment terms not provided."
            )

        # -----------------------------------------------------
        # Metadata
        # -----------------------------------------------------

        metadata = {
            "document_type": document.document_type.value,
            "currency": document.currency,
            "document_date": document.document_date,
            "due_date": document.due_date,
        }

        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=100,
            summary="Compliance validation completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata=metadata,
        )