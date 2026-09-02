"""
============================================================
Vendor Check Module

Verification Module 3

Responsibilities
----------------
- Verify vendor exists
- Check verification status
- Check blocked status
- Evaluate vendor risk
- Detect unusual spending

No database.
No repositories.
============================================================
"""

from __future__ import annotations

from decimal import Decimal

from app.models.domain.document import Document
from app.models.domain.vendor import Vendor
from app.services.verification.result import VerificationResult


class VendorCheck:
    """
    Vendor intelligence validation.
    """

    HIGH_RISK_SCORE = 80

    SPEND_MULTIPLIER = Decimal("3.0")

    async def run(
        self,
        document: Document,
        vendor: Vendor | None,
    ) -> VerificationResult:

        passed = True

        score = 100

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        metadata: dict = {}

        # -----------------------------------------------------
        # Vendor Exists
        # -----------------------------------------------------

        if vendor is None:

            return VerificationResult(
                passed=False,
                score=0,
                confidence=100,
                summary="Vendor not found.",
                reasons=["Vendor does not exist."],
                positives=[],
                warnings=[],
                metadata={},
            )

        # -----------------------------------------------------
        # Blocked Vendor
        # -----------------------------------------------------

        if vendor.is_blocked:

            passed = False

            score -= 50

            reasons.append(
                "Vendor is blocked."
            )

        else:

            positives.append(
                "Vendor is active."
            )

        # -----------------------------------------------------
        # Verification
        # -----------------------------------------------------

        if vendor.is_verified:

            positives.append(
                "Vendor is verified."
            )

        else:

            warnings.append(
                "Vendor has not been verified."
            )

            score -= 10

        # -----------------------------------------------------
        # Risk Score
        # -----------------------------------------------------

        if vendor.risk_score >= self.HIGH_RISK_SCORE:

            passed = False

            score -= 30

            reasons.append(
                "Vendor risk score is high."
            )

        # -----------------------------------------------------
        # Fraud History
        # -----------------------------------------------------

        if vendor.fraud_flags > 0:

            warnings.append(
                f"{vendor.fraud_flags} historical fraud flags."
            )

            score -= 10

        # -----------------------------------------------------
        # Spending Pattern
        # -----------------------------------------------------

        if (
            document.total_amount is not None
            and vendor.average_spend > 0
        ):

            threshold = (
                vendor.average_spend
                * self.SPEND_MULTIPLIER
            )

            if document.total_amount > threshold:

                warnings.append(
                    "Invoice amount is unusually high for this vendor."
                )

                score -= 15

        # -----------------------------------------------------
        # Metadata
        # -----------------------------------------------------

        metadata = {
            "vendor_id": vendor.id,
            "risk_score": vendor.risk_score,
            "risk_level": vendor.risk_level,
            "fraud_flags": vendor.fraud_flags,
            "average_spend": vendor.average_spend,
            "document_total": document.total_amount,
        }

        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=100,
            summary="Vendor validation completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata=metadata,
        )