"""
============================================================
Math Check Module

Verification Module 2

Responsibilities
----------------
- Validate invoice mathematics
- Verify line item totals
- Verify subtotal
- Verify tax
- Verify grand total

No database.
No repositories.
============================================================
"""

from __future__ import annotations

from decimal import Decimal

from app.models.domain.document import (
    Document,
    DocumentLineItem,
)
from app.services.verification.result import (
    VerificationResult,
)


class MathCheck:
    """
    Mathematical validation.
    """

    TOLERANCE = Decimal("0.01")

    async def run(
        self,
        document: Document,
        line_items: list[DocumentLineItem],
    ) -> VerificationResult:

        passed = True

        score = 100

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        # -----------------------------------------------------
        # Line Item Validation
        # -----------------------------------------------------

        calculated_subtotal = Decimal("0")

        for item in line_items:

            expected = item.quantity * item.unit_price

            if item.discount:
                expected -= item.discount

            if abs(expected - item.amount) > self.TOLERANCE:

                passed = False

                score -= 10

                reasons.append(
                    f"Line item '{item.description}' total mismatch."
                )

            calculated_subtotal += item.amount

        # -----------------------------------------------------
        # Subtotal
        # -----------------------------------------------------

        if document.subtotal is not None:

            if abs(document.subtotal - calculated_subtotal) > self.TOLERANCE:

                passed = False

                score -= 20

                reasons.append(
                    "Subtotal does not match line items."
                )

            else:

                positives.append(
                    "Subtotal validated."
                )

        # -----------------------------------------------------
        # Grand Total
        # -----------------------------------------------------

        if (
            document.subtotal is not None
            and document.tax_amount is not None
            and document.total_amount is not None
        ):

            expected_total = (
                document.subtotal
                + document.tax_amount
                - (document.discount_amount or Decimal("0"))
            )

            if abs(expected_total - document.total_amount) > self.TOLERANCE:

                passed = False

                score -= 30

                reasons.append(
                    "Grand total calculation is incorrect."
                )

            else:

                positives.append(
                    "Grand total validated."
                )

        # -----------------------------------------------------
        # Build Result
        # -----------------------------------------------------

        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=100,
            summary="Mathematical validation completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata={
                "calculated_subtotal": calculated_subtotal,
                "subtotal": document.subtotal,
                "tax": document.tax_amount,
                "total": document.total_amount,
            },
        )