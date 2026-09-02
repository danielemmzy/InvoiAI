"""
============================================================
Price Increase Detector

Flow 10 — "price_increase_detector: IF increase_pct > 10% ->
insights INSERT: type=price_increase, severity=warning".
============================================================
"""

from __future__ import annotations

from app.core.enum.insight import InsightSeverity, InsightType
from app.services.insights.result import AnalyzerResult

THRESHOLD_PCT = 10.0


class PriceIncreaseDetector:
    def detect(self, vendor_result: AnalyzerResult) -> dict | None:
        top = vendor_result.data.get("top_increase")

        if not top or top.get("increase_pct", 0) <= THRESHOLD_PCT:
            return None

        return {
            "insight_type": InsightType.PRICE_INCREASE,
            "severity": InsightSeverity.WARNING,
            "title": f"{top['vendor_name']} charged {top['increase_pct']}% more than usual",
            "description": (
                f"{top['vendor_name']}'s latest invoice was "
                f"${top['latest_amount']:,.2f} vs a 12-month average of "
                f"${top['avg_amount']:,.2f}."
            ),
            "data": top,
            "recommended_action": "Request a quote from alternative suppliers",
        }
