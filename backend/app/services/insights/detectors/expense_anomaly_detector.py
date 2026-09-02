"""
============================================================
Expense Anomaly Detector

Flow 10 — "expense_anomaly_detector: IF category MoM spike >
20% -> insights INSERT: type=anomaly, severity=warning".
============================================================
"""

from __future__ import annotations

from app.core.enum.insight import InsightSeverity, InsightType
from app.services.insights.result import AnalyzerResult

THRESHOLD_PCT = 20.0


class ExpenseAnomalyDetector:
    def detect(self, spending_result: AnalyzerResult) -> dict | None:
        top = spending_result.data.get("top_spike")

        if not top or top.get("increase_pct", 0) <= THRESHOLD_PCT:
            return None

        return {
            "insight_type": InsightType.ANOMALY,
            "severity": InsightSeverity.WARNING,
            "title": f"{top['category'].title()} expenses up {top['increase_pct']}% this month",
            "description": (
                f"{top['category'].title()} spending this month is "
                f"${top['current_month_total']:,.2f} vs an average of "
                f"${top['average_total']:,.2f}."
            ),
            "data": top,
            "recommended_action": "Review recent transactions in this category",
        }
