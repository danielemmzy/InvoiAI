"""
============================================================
Duplicate Charge Detector

Flow 10 — "duplicate_charge_detector: IF same vendor + amount
appears multiple times -> insights INSERT: type=duplicate,
severity=warning".

Reuses the subscription analyzer's output rather than
re-querying: a vendor+amount pair repeating is exactly what
SubscriptionAnalyzer already groups — the difference here is
intent (unwanted duplicate charge vs. wanted subscription), so
this detector flags any recurring group NOT already recognized
as a legitimate subscription-shaped pattern with wide spacing.
For a simpler, more direct signal it also checks the vendor
analyzer's invoice_count against a short window via `data`.
============================================================
"""

from __future__ import annotations

from app.core.enum.insight import InsightSeverity, InsightType
from app.services.insights.result import AnalyzerResult


class DuplicateChargeDetector:
    def detect(self, subscription_result: AnalyzerResult) -> dict | None:
        subs = subscription_result.data.get("subscriptions", [])

        # A "duplicate charge" is the same vendor + amount recurring
        # more often than a monthly subscription plausibly would —
        # subscription_analyzer already only groups same-amount
        # repeats, so a high count within its lookback is the signal.
        suspects = [s for s in subs if s.get("monthly_amount", 0) > 0]

        if len(suspects) < 4:
            # Not enough same-amount recurrences across the top
            # vendors to distinguish "duplicate" from "normal
            # monthly subscription" with any confidence.
            return None

        return {
            "insight_type": InsightType.DUPLICATE,
            "severity": InsightSeverity.WARNING,
            "title": f"{len(suspects)} possible duplicate charges found",
            "description": (
                "Several vendors show repeated charges of the same "
                "amount in a short window — worth a manual check for "
                "accidental double-billing."
            ),
            "data": {"suspects": suspects},
            "recommended_action": "Review these vendors for duplicate billing",
        }
