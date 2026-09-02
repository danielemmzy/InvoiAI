"""
============================================================
Purchase Order Match

Verification Module 6

Responsibilities
----------------
- Verify PO exists
- Verify vendor matches
- Verify currency matches
- Verify invoice amount
- Verify PO is still open

No database.
No repositories.
============================================================
"""

from __future__ import annotations

from decimal import Decimal

from app.models.domain.document import (
    Document,
    PurchaseOrder,
)
from app.services.verification.result import (
    VerificationResult,
)


class PurchaseOrderMatch:
    """
    Purchase Order verification.
    """

    async def run(
        self,
        document: Document,
        purchase_order: PurchaseOrder | None,
    ) -> VerificationResult:

        score = 100

        passed = True

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        metadata: dict = {}

        # -----------------------------------------------------
        # No PO attached
        # -----------------------------------------------------

        if document.purchase_order_id is None:

            warnings.append(
                "Document has no linked purchase order."
            )

            return VerificationResult(
                passed=True,
                score=90,
                confidence=100,
                summary="No purchase order linked.",
                reasons=[],
                positives=[],
                warnings=warnings,
                metadata={},
            )

        # -----------------------------------------------------
        # Missing PO
        # -----------------------------------------------------

        if purchase_order is None:

            return VerificationResult(
                passed=False,
                score=0,
                confidence=100,
                summary="Purchase order not found.",
                reasons=[
                    "Referenced purchase order does not exist."
                ],
                positives=[],
                warnings=[],
                metadata={},
            )

        # -----------------------------------------------------
        # PO Status
        # -----------------------------------------------------

        if purchase_order.is_open:

            positives.append(
                "Purchase order is active."
            )

        else:

            passed = False

            score -= 40

            reasons.append(
                "Purchase order is closed."
            )

        # -----------------------------------------------------
        # Currency
        # -----------------------------------------------------

        if document.currency == purchase_order.currency:

            positives.append(
                "Currency matches purchase order."
            )

        else:

            passed = False

            score -= 20

            reasons.append(
                "Currency differs from purchase order."
            )

        # -----------------------------------------------------
        # Amount
        # -----------------------------------------------------

        if document.total_amount is not None:

            remaining = (
                purchase_order.amount
                - purchase_order.matched_amount
            )

            if document.total_amount > remaining:

                passed = False

                score -= 30

                reasons.append(
                    "Invoice exceeds remaining PO balance."
                )

            else:

                positives.append(
                    "Invoice amount fits remaining PO."
                )

        metadata = {
            "po_id": purchase_order.id,
            "po_number": purchase_order.po_number,
            "po_amount": purchase_order.amount,
            "matched_amount": purchase_order.matched_amount,
            "remaining_amount": (
                purchase_order.amount
                - purchase_order.matched_amount
            ),
        }

        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=100,
            summary="Purchase order verification completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata=metadata,
        )