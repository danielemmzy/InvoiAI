"""
============================================================
Verification Engine

Coordinates all verification modules.

Responsibilities
----------------
- Execute verification modules
- Merge results
- Calculate overall score
- Determine recommendation

No SQL.
No repositories.
No persistence.
============================================================
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core.enum.database import (
    RecommendationType,
    RiskLevel,
)

from app.models.domain.document import (
    Document,
    OCRResult,
)


class VerificationEngine:
    """
    Runs every verification module.
    """

    def __init__(
        self,
        ocr_validation,
        math_check,
        vendor_check,
        duplicate_check,
        historical_check,
        po_match,
        fraud_check,
        compliance_check,
    ):

        self.ocr_validation = ocr_validation
        self.math_check = math_check
        self.vendor_check = vendor_check
        self.duplicate_check = duplicate_check
        self.historical_check = historical_check
        self.po_match = po_match
        self.fraud_check = fraud_check
        self.compliance_check = compliance_check


    async def verify(
        self,
        document: Document,
        ocr: OCRResult,
        *,
        line_items=None,
        vendor=None,
        purchase_order=None,
        duplicate_document=None,
        progress_callback: Callable[[str, str, int], Awaitable[None]] | None = None,
    ) -> dict:
        """
        Execute complete verification pipeline.
        """


        # =====================================================
        # OCR
        # =====================================================

        if progress_callback:
            await progress_callback("ocr_check", "Checking OCR quality and extracted text", 48)

        ocr_result = await self.ocr_validation.run(
            ocr,
        )


        # =====================================================
        # Mathematics
        # =====================================================

        if progress_callback:
            await progress_callback("math_check", "Checking invoice math, totals, tax, and line items", 55)

        math_result = await self.math_check.run(
            document,
            line_items or [],
        )


        # =====================================================
        # Vendor
        # =====================================================

        if progress_callback:
            await progress_callback("vendor_check", "Comparing the vendor with its financial history", 63)

        vendor_result = await self.vendor_check.run(
            document,
            vendor,
        )


        # =====================================================
        # Duplicate
        # =====================================================

        if progress_callback:
            await progress_callback("duplicate_check", "Checking for duplicate or highly similar documents", 70)

        duplicate_result = await self.duplicate_check.run(
            document,
            duplicate_document,
        )


        # =====================================================
        # Historical
        # =====================================================

        historical_result = None

        if vendor:

            if progress_callback:
                await progress_callback("historical_check", "Comparing against historical vendor patterns", 76)

            historical_result = await self.historical_check.run(
                document,
                vendor,
            )


        # =====================================================
        # Purchase Order
        # =====================================================

        if progress_callback:
            await progress_callback("purchase_order_check", "Checking related purchase order information", 80)

        po_result = await self.po_match.run(
            document,
            purchase_order,
        )


        # =====================================================
        # Fraud
        # =====================================================

        if progress_callback:
            await progress_callback("fraud_check", "Running fraud, anomaly, and risk checks", 86)

        fraud_result = await self.fraud_check.run(
            document,
            vendor,
        )


        # =====================================================
        # Compliance
        # =====================================================

        if progress_callback:
            await progress_callback("compliance_check", "Checking compliance and policy signals", 90)

        compliance_result = await self.compliance_check.run(
            document,
        )


        results = [
            ocr_result,
            math_result,
            vendor_result,
            duplicate_result,
            historical_result,
            po_result,
            fraud_result,
            compliance_result,
        ]


        available_results = [
            result
            for result in results
            if result is not None
            and result.metadata.get("available", True) is not False
        ]

        scores = [result.score for result in available_results]
        overall_score = int(sum(scores) / len(scores)) if scores else 0
        unavailable_modules = [
            name
            for name, result in (
                ("ocr", ocr_result),
                ("math", math_result),
                ("vendor", vendor_result),
                ("duplicate", duplicate_result),
                ("historical", historical_result),
                ("purchase_order", po_result),
                ("fraud", fraud_result),
                ("compliance", compliance_result),
            )
            if result is not None and result.metadata.get("available", True) is False
        ]


        # =====================================================
        # Decision
        # =====================================================

        if overall_score >= 85:
            risk = RiskLevel.LOW
            recommendation = RecommendationType.APPROVE
        elif overall_score >= 70:
            risk = RiskLevel.MEDIUM
            recommendation = RecommendationType.REVIEW
        elif overall_score >= 50:
            risk = RiskLevel.HIGH
            recommendation = RecommendationType.REVIEW
        else:
            risk = RiskLevel.CRITICAL
            recommendation = RecommendationType.REJECT

        # Missing platform/business context is not the same thing as a fraud
        # signal. It prevents automatic approval but must not manufacture a
        # zero risk score. The affected module remains explicitly unavailable.
        if unavailable_modules:
            recommendation = RecommendationType.REVIEW
            if risk == RiskLevel.LOW:
                risk = RiskLevel.MEDIUM



        return {

            "health_score": overall_score,

            "overall_score": overall_score,


            "financial_score":
                math_result.score,


            "fraud_score":
                fraud_result.score,


            "duplicate_score":
                duplicate_result.score,


            "vendor_score":
                vendor_result.score,


            "policy_score":
                compliance_result.score,


            "risk_level": risk,


            "recommendation": recommendation,


            "summary": (
                f"Overall document health score: {overall_score}/100."
                + (
                    " Some checks require additional information: "
                    + ", ".join(unavailable_modules) + "."
                    if unavailable_modules
                    else ""
                )
            ),
            "unavailable_modules": unavailable_modules,



            "module_results": {

                "ocr": ocr_result,

                "math": math_result,

                "vendor": vendor_result,

                "duplicate": duplicate_result,

                "historical": historical_result,

                "purchase_order": po_result,

                "fraud": fraud_result,

                "compliance": compliance_result,

            },


            "reasons": {

                "ocr":
                    ocr_result.metadata,


                "math":
                    math_result.metadata,


                "vendor":
                    vendor_result.metadata,


                "duplicate":
                    duplicate_result.metadata,


                "historical":
                    historical_result.metadata
                    if historical_result
                    else {},


                "purchase_order":
                    po_result.metadata,


                "fraud":
                    fraud_result.metadata,


                "compliance":
                    compliance_result.metadata,

            },

        }