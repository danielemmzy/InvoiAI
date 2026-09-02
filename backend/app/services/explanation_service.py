"""
============================================================
Explanation Service

Responsible for generating human-readable AI explanations.

Responsibilities
----------------
- Explain overall decision
- Explain risk
- Explain score
- Explain recommendation
- Explain fraud findings
- Explain OCR confidence

NO SQL.
NO repositories.
NO OpenAI calls.

Later this service can delegate to GPT-5 or another LLM.
============================================================
"""

from __future__ import annotations

from app.models.domain.analysis import Analysis


class ExplanationService:
    """
    Converts analysis results into
    human-readable explanations.
    """

    # =========================================================
    # Overall
    # =========================================================

    async def overall_summary(
        self,
        analysis: Analysis,
    ) -> str:

        return analysis.summary

    # =========================================================
    # Health Score
    # =========================================================

    async def health_score(
        self,
        analysis: Analysis,
    ) -> str:

        score = analysis.health_score

        if score >= 90:
            return (
                "The document appears healthy with very few "
                "issues detected."
            )

        if score >= 70:
            return (
                "The document is generally healthy but has "
                "minor warnings."
            )

        if score >= 50:
            return (
                "The document contains several issues that "
                "should be reviewed."
            )

        return (
            "The document has significant problems and "
            "requires attention."
        )

    # =========================================================
    # Risk
    # =========================================================

    async def risk(
        self,
        analysis: Analysis,
    ) -> str:

        return (
            f"Overall risk level: "
            f"{analysis.risk_level}."
        )

    # =========================================================
    # Recommendation
    # =========================================================

    async def recommendation(
        self,
        analysis: Analysis,
    ) -> str:

        return (
            f"Recommended action: "
            f"{analysis.recommendation.value}."
        )

    # =========================================================
    # Fraud
    # =========================================================

    async def fraud(
        self,
        analysis: Analysis,
    ) -> str:

        if not analysis.fraud_signals:

            return (
                "No fraud indicators were detected."
            )

        signals = ", ".join(
            signal.value
            for signal in analysis.fraud_signals
        )

        return (
            f"Fraud indicators detected: {signals}."
        )

    # =========================================================
    # OCR
    # =========================================================

    async def ocr(
        self,
        analysis: Analysis,
    ) -> str:

        return (
            f"OCR confidence was "
            f"{analysis.ocr_confidence}%."
        )

    # =========================================================
    # Math
    # =========================================================

    async def math(
        self,
        analysis: Analysis,
    ) -> str:

        if analysis.math_passed:

            return (
                "Mathematical validation passed."
            )

        return (
            "Mathematical validation detected "
            "a discrepancy."
        )

    # =========================================================
    # Vendor
    # =========================================================

    async def vendor(
        self,
        analysis: Analysis,
    ) -> str:

        if analysis.vendor_known:

            return (
                "Vendor has previous transaction history."
            )

        return (
            "Vendor has no historical records."
        )

    # =========================================================
    # Duplicate
    # =========================================================

    async def duplicate(
        self,
        analysis: Analysis,
    ) -> str:

        if analysis.is_duplicate:

            return (
                "Possible duplicate document detected."
            )

        return (
            "No duplicate document detected."
        )

    # =========================================================
    # Compliance
    # =========================================================

    async def compliance(
        self,
        analysis: Analysis,
    ) -> str:

        if analysis.compliance_passed:

            return (
                "Compliance checks passed."
            )

        return (
            "Compliance issues were detected."
        )

    # =========================================================
    # Full Explanation
    # =========================================================

    async def build(
        self,
        analysis: Analysis,
    ) -> dict:

        return {
            "summary": await self.overall_summary(
                analysis,
            ),
            "health": await self.health_score(
                analysis,
            ),
            "risk": await self.risk(
                analysis,
            ),
            "recommendation": await self.recommendation(
                analysis,
            ),
            "fraud": await self.fraud(
                analysis,
            ),
            "ocr": await self.ocr(
                analysis,
            ),
            "math": await self.math(
                analysis,
            ),
            "vendor": await self.vendor(
                analysis,
            ),
            "duplicate": await self.duplicate(
                analysis,
            ),
            "compliance": await self.compliance(
                analysis,
            ),
        }