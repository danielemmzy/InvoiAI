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

from decimal import Decimal, InvalidOperation

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

    @staticmethod
    def _decimal(value: object, default: Decimal) -> Decimal:
        if value is None or value == "":
            return default
        try:
            return Decimal(str(value).replace(",", "").strip())
        except (InvalidOperation, ValueError, TypeError):
            return default

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
            # DocumentRepository returns Supabase rows as dictionaries.
            # The verification layer must accept that persistence shape;
            # do not assume callers have already converted rows into
            # DocumentLineItem Pydantic objects.
            if isinstance(item, dict):
                description = str(item.get("description") or "Line item")
                quantity = self._decimal(item.get("quantity"), Decimal("1"))
                unit_price = self._decimal(item.get("unit_price"), Decimal("0"))
                amount = self._decimal(item.get("amount"), Decimal("0"))
                discount = self._decimal(item.get("discount"), Decimal("0"))
            else:
                description = item.description
                quantity = self._decimal(item.quantity, Decimal("1"))
                unit_price = self._decimal(item.unit_price, Decimal("0"))
                amount = self._decimal(item.amount, Decimal("0"))
                discount = self._decimal(item.discount, Decimal("0"))

            expected = quantity * unit_price - discount

            if abs(expected - amount) > self.TOLERANCE:

                passed = False

                score -= 10

                reasons.append(
                    f"Line item '{description}' total mismatch."
                )

            calculated_subtotal += amount

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

        expected_total: Decimal | None = None
        variance: Decimal | None = None

        if document.subtotal is not None and document.total_amount is not None:
            if document.tax_amount is None:
                expected_without_tax = document.subtotal - (document.discount_amount or Decimal("0"))
                if abs(expected_without_tax - document.total_amount) > self.TOLERANCE:
                    passed = False
                    score -= 30
                    reasons.append("Grand total cannot be fully reconciled without tax amount.")
            else:
                expected_total = (
                    document.subtotal
                    + document.tax_amount
                    - (document.discount_amount or Decimal("0"))
                )
                variance = document.total_amount - expected_total

                if abs(variance) > self.TOLERANCE:

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
                "expected_total": expected_total,
                "actual_total": document.total_amount,
                "variance": variance,
            },
        )
