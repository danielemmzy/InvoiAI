from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.models.domain.analysis import Analysis
from app.models.domain.document import (
    Document,
    OCRResult,
)


class AnalysisBuilder:
    """
    Builds Analysis domain object from
    VerificationEngine output.
    """

    @staticmethod
    def build(
        document: Document,
        ocr: OCRResult,
        verification: dict,
    ) -> Analysis:

        now = datetime.now(UTC)

        reasons = verification.get(
            "reasons",
            {},
        )

        fraud_data = reasons.get(
            "fraud",
            {},
        )

        vendor_data = reasons.get(
            "vendor",
            {},
        )

        math_data = reasons.get(
            "math",
            {},
        )

        duplicate_data = reasons.get(
            "duplicate",
            {},
        )


        return Analysis(

            # =================================================
            # Identity
            # =================================================

            id=uuid4(),

            document_id=document.id,

            org_id=document.org_id,


            # =================================================
            # Decision
            # =================================================

            health_score=verification.get(
                "health_score",
                0,
            ),

            overall_score=verification.get(
                "overall_score",
                0,
            ),

            risk_level=verification.get(
                "risk_level",
            ),

            recommendation=verification.get(
                "recommendation",
            ),

            summary=verification.get(
                "summary",
                "",
            ),


            # =================================================
            # Scores
            # =================================================

            financial_score=verification.get(
                "financial_score",
                0,
            ),

            fraud_score=verification.get(
                "fraud_score",
                0,
            ),

            duplicate_score=verification.get(
                "duplicate_score",
                100,
            ),

            vendor_score=verification.get(
                "vendor_score",
                0,
            ),

            policy_score=verification.get(
                "policy_score",
                0,
            ),


            # =================================================
            # OCR
            # =================================================

            confidence_score=int(
                ocr.confidence_score * 100
            ),

            ocr_confidence=int(
                ocr.confidence_score * 100
            ),


            # =================================================
            # Evidence
            # =================================================

            reasons=reasons,

            positive_signals={},

            action_items={},

            module_results=verification.get(
                "module_results",
                {},
            ),


            # =================================================
            # Math
            # =================================================

            math_passed=math_data.get(
                "passed",
                True,
            ),

            math_expected_total=(
                document.total_amount
                or Decimal("0")
            ),

            math_actual_total=(
                document.total_amount
                or Decimal("0")
            ),

            math_variance=Decimal("0"),


            # =================================================
            # Vendor
            # =================================================

            vendor_known=bool(
                vendor_data
            ),

            vendor_risk_score=vendor_data.get(
                "risk_score",
                0,
            ),


            # =================================================
            # Duplicate
            # =================================================

            is_duplicate=duplicate_data.get(
                "duplicate_found",
                False,
            ),

            duplicate_of=duplicate_data.get(
                "duplicate_document_id",
            ),

            duplicate_similarity=duplicate_data.get(
                "similarity",
            ),


            # =================================================
            # Amount Anomaly
            # =================================================

            amount_anomaly=False,

            amount_vs_avg_pct=None,

            std_deviations_from_avg=None,


            # =================================================
            # Purchase Order
            # =================================================

            po_matched=False,

            po_id=document.purchase_order_id,


            # =================================================
            # Fraud
            # =================================================

            fraud_signals=fraud_data.get(
                "fraud_signals",
                [],
            ),


            # =================================================
            # Compliance
            # =================================================

            compliance_passed=True,


            # =================================================
            # Human Review
            # =================================================

            reviewed_by=None,

            reviewed_at=None,

            final_decision=None,

            override_reason=None,


            # =================================================
            # Engine Metadata
            # =================================================

            model="rule-based",

            engine_version="1.0",

            analysis_version="1.0",

            prompt_version=None,

            temperature=Decimal("0"),


            # =================================================
            # Processing
            # =================================================

            processing_ms=ocr.processing_ms,

            tokens_used=0,

            tokens_cost_usd=Decimal("0"),


            created_at=now,

            updated_at=now,
        )