"""
============================================================
Cashflow Detector

Flow 10 — "cashflow_detector: IF cash_runway_days < 60 ->
insights INSERT: type=cashflow, severity=critical".
============================================================
"""

from __future__ import annotations

from app.core.enum.insight import InsightSeverity, InsightType
from app.services.insights.result import AnalyzerResult

RUNWAY_THRESHOLD_DAYS = 60


class CashflowDetector:
    def detect(self, cashflow_result: AnalyzerResult) -> dict | None:
        runway = cashflow_result.data.get("cash_runway_days")

        if runway is None or runway >= RUNWAY_THRESHOLD_DAYS:
            return None

        return {
            "insight_type": InsightType.CASHFLOW,
            "severity": InsightSeverity.CRITICAL,
            "title": f"Cash runway is only {runway} days",
            "description": (
                f"At the current burn rate, projected cash runway is "
                f"{runway} days."
            ),
            "data": cashflow_result.data,
            "recommended_action": "Review upcoming payables and accelerate collections",
        }
