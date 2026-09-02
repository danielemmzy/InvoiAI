"""
============================================================
Fraud Check

Verification Module 7

Responsibilities
----------------
- Detect vendor fraud indicators
- Detect suspicious banking changes
- Detect duplicate history
- Detect excessive fraud flags
- Produce fraud score

No database.
No repositories.
============================================================
"""

from __future__ import annotations

from app.models.domain.document import Document
from app.models.domain.vendor import Vendor
from app.services.verification.result import VerificationResult


class FraudCheck:
    """
    Fraud detection heuristics.
    """

    MAX_BANK_CHANGES = 3

    MAX_FRAUD_FLAGS = 3

    MAX_DUPLICATES = 5

    async def run(
        self,
        document: Document,
        vendor: Vendor | None,
    ) -> VerificationResult:

        score = 100

        passed = True

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        metadata: dict = {}

        # -----------------------------------------------------
        # Vendor Missing
        # -----------------------------------------------------

        if vendor is None:

            return VerificationResult(
                passed=False,
                score=0,
                confidence=100,
                summary="Vendor unavailable for fraud analysis.",
                reasons=[
                    "Vendor record not found."
                ],
                positives=[],
                warnings=[],
                metadata={},
            )

        # -----------------------------------------------------
        # Vendor Blocked
        # -----------------------------------------------------

        if vendor.is_blocked:

            passed = False

            score -= 50

            reasons.append(
                "Vendor is blocked."
            )

        # -----------------------------------------------------
        # Fraud Flags
        # -----------------------------------------------------

        if vendor.fraud_flags >= self.MAX_FRAUD_FLAGS:

            passed = False

            score -= 25

            reasons.append(
                "Vendor has multiple historical fraud flags."
            )

        elif vendor.fraud_flags > 0:

            warnings.append(
                "Vendor has previous fraud history."
            )

            score -= 10

        else:

            positives.append(
                "No historical fraud flags."
            )

        # -----------------------------------------------------
        # Duplicate History
        # -----------------------------------------------------

        if vendor.duplicate_count >= self.MAX_DUPLICATES:

            warnings.append(
                "Vendor has many duplicate submissions."
            )

            score -= 10

        # -----------------------------------------------------
        # Bank Changes
        # -----------------------------------------------------

        if vendor.bank_change_count >= self.MAX_BANK_CHANGES:

            warnings.append(
                "Vendor banking information changed frequently."
            )

            score -= 20

        else:

            positives.append(
                "Stable banking information."
            )

        # -----------------------------------------------------
        # Vendor Risk
        # -----------------------------------------------------

        if vendor.risk_score >= 80:

            passed = False

            score -= 20

            reasons.append(
                "Vendor risk score is high."
            )

        metadata = {
            "risk_score": vendor.risk_score,
            "fraud_flags": vendor.fraud_flags,
            "duplicate_count": vendor.duplicate_count,
            "bank_change_count": vendor.bank_change_count,
            "vendor_verified": vendor.is_verified,
            "document_id": document.id,
        }

        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=100,
            summary="Fraud analysis completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata=metadata,
        )