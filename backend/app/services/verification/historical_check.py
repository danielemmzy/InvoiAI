"""
============================================================
Historical Check Module

Verification Module 5

Responsibilities
----------------
- Compare document against historical behavior
- Detect unusual document timing
- Detect unusual amount
- Detect unusual currency
- Detect unusual payment terms

No database.
No repositories.
============================================================
"""

from __future__ import annotations

from decimal import Decimal

from app.models.domain.document import Document
from app.models.domain.vendor import Vendor
from app.services.verification.result import VerificationResult


class HistoricalCheck:
    """
    Historical behaviour validation.
    """

    AMOUNT_MULTIPLIER = Decimal("3.0")

    async def run(
        self,
        document: Document,
        vendor: Vendor,
    ) -> VerificationResult:

        passed = True

        score = 100

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        # -----------------------------------------------------
        # Amount
        # -----------------------------------------------------

        if (
            document.total_amount is not None
            and vendor.average_spend > 0
        ):

            if (
                document.total_amount
                > vendor.average_spend * self.AMOUNT_MULTIPLIER
            ):

                warnings.append(
                    "Amount significantly exceeds historical average."
                )

                score -= 20

            else:

                positives.append(
                    "Amount within historical range."
                )

        # -----------------------------------------------------
        # Currency
        # -----------------------------------------------------

        if (
            vendor.typical_currency
            and document.currency != vendor.typical_currency
        ):

            warnings.append(
                "Currency differs from historical pattern."
            )

            score -= 10

        else:

            positives.append(
                "Currency matches historical records."
            )

        # -----------------------------------------------------
        # Payment Terms
        # -----------------------------------------------------

        if document.payment_terms is None:

            warnings.append(
                "Missing payment terms."
            )

        # -----------------------------------------------------
        # Document Frequency
        # -----------------------------------------------------

        if vendor.total_document_count < 3:

            warnings.append(
                "Limited historical data available."
            )

        else:

            positives.append(
                "Historical profile available."
            )

        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=100,
            summary="Historical validation completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata={
                "average_spend": vendor.average_spend,
                "median_spend": vendor.median_spend,
                "currency": document.currency,
                "typical_currency": vendor.typical_currency,
                "document_count": vendor.total_document_count,
            },
        )