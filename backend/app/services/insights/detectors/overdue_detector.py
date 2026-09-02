"""
============================================================
Overdue Detector

Flow 10 — "overdue_detector: IF overdue_amount > 0 -> insights
INSERT: type=overdue, severity=critical".
============================================================
"""

from __future__ import annotations

from app.core.enum.insight import InsightSeverity, InsightType
from app.services.insights.result import AnalyzerResult


class OverdueDetector:
    def detect(self, receivable_result: AnalyzerResult) -> dict | None:
        data = receivable_result.data
        overdue_amount = data.get("overdue_amount", 0)

        if not overdue_amount or overdue_amount <= 0:
            return None

        overdue_count = data.get("overdue_count", 0)

        return {
            "insight_type": InsightType.OVERDUE,
            "severity": InsightSeverity.CRITICAL,
            "title": f"${overdue_amount:,.0f} at risk across {overdue_count} invoices",
            "description": (
                f"{overdue_count} invoice(s) totalling ${overdue_amount:,.2f} "
                f"are past their due date."
            ),
            "data": data,
            "recommended_action": "Send payment reminders",
        }
