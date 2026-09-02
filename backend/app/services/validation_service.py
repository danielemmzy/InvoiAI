"""
============================================================
Validation Service

Business validation before AI analysis.

Responsibilities
----------------
- Validate required fields
- Validate dates
- Validate amounts
- Validate currency
- Validate document number
- Execute mathematical validation
- Return validation result

No SQL.
No repositories.
============================================================
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.domain.document import (
    Document,
    DocumentLineItem,
)
from app.models.domain.validation import ValidationResult
from app.services.verification.math_check import MathCheck


class ValidationService:
    """
    Performs business validation before AI verification.

    NOTE: this file was previously named "validation service.py"
    (with a literal space in the filename), which meant nothing in
    the codebase could import it. Renamed to validation_service.py
    and given math_check a self-constructing default so it can be
    instantiated the same way the rest of the service layer is
    (see app/services/organization_service.py for the convention).
    """

    SUPPORTED_CURRENCIES = {
        "USD",
        "EUR",
        "GBP",
        "NGN",
        "CAD",
        "AUD",
        "JPY",
        "CNY",
    }

    def __init__(
        self,
        math_check: MathCheck | None = None,
    ):
        self.math_check = math_check or MathCheck()

    async def validate(
        self,
        document: Document,
        line_items: list[DocumentLineItem],
    ) -> ValidationResult:

        warnings: list[str] = []
        errors: list[str] = []

        # =====================================================
        # Required Fields
        # =====================================================

        if not document.document_number:
            warnings.append(
                "Document number is missing."
            )

        if not document.vendor_name:
            warnings.append(
                "Vendor name is missing."
            )

        if document.total_amount is None:
            errors.append(
                "Total amount is required."
            )

        if document.currency is None:
            errors.append(
                "Currency is required."
            )

        # =====================================================
        # Currency
        # =====================================================

        if (
            document.currency
            and document.currency
            not in self.SUPPORTED_CURRENCIES
        ):
            warnings.append(
                f"Unsupported currency '{document.currency}'."
            )

        # =====================================================
        # Dates
        # =====================================================

        today = date.today()

        if (
            document.document_date
            and document.document_date > today
        ):
            warnings.append(
                "Document date is in the future."
            )

        if (
            document.due_date
            and document.document_date
            and document.due_date < document.document_date
        ):
            warnings.append(
                "Due date occurs before document date."
            )

        # =====================================================
        # Amounts
        # =====================================================

        if (
            document.total_amount is not None
            and document.total_amount < Decimal("0")
        ):
            errors.append(
                "Total amount cannot be negative."
            )

        if (
            document.subtotal is not None
            and document.subtotal < Decimal("0")
        ):
            errors.append(
                "Subtotal cannot be negative."
            )

        if (
            document.tax_amount is not None
            and document.tax_amount < Decimal("0")
        ):
            warnings.append(
                "Negative tax amount detected."
            )

        # =====================================================
        # Line Items
        # =====================================================

        if not line_items:
            warnings.append(
                "Document contains no line items."
            )

        # =====================================================
        # Mathematical Validation
        # =====================================================

        math_result = await self.math_check.run(
            document,
            line_items,
        )

        warnings.extend(
            math_result.warnings
        )

        errors.extend(
            math_result.reasons
        )

        # =====================================================
        # Result
        # =====================================================

        return ValidationResult(
            passed=len(errors) == 0,
            warnings=warnings,
            errors=errors,
            metadata={
                "math_score": math_result.score,
                "math_passed": math_result.passed,
                "math_confidence": math_result.confidence,
            },
        )
