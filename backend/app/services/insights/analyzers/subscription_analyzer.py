"""
============================================================
Subscription Analyzer

Flow 10 — "subscription_analyzer.run(org_id) -> recurring
charges detected by same vendor + amount, unused = no related
docs in 30 days". Pure Python math. No LLM.
============================================================
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repositories.document.vendor_repository import VendorRepository
from app.repositories.document.document_repository import DocumentRepository
from app.services.insights.result import AnalyzerResult

MIN_OCCURRENCES_FOR_RECURRING = 2
UNUSED_THRESHOLD_DAYS = 30


class SubscriptionAnalyzer:
    def __init__(
        self,
        vendor_repository: VendorRepository | None = None,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self.vendors = vendor_repository or VendorRepository()
        self.documents = document_repository or DocumentRepository()

    async def run(self, org_id: UUID, top_n: int = 25) -> AnalyzerResult:
        vendors = await self.vendors.top_vendors_by_documents(org_id, limit=top_n)

        subscriptions = []
        unused = []
        total_monthly = 0.0
        now = datetime.now(UTC).date()

        for vendor in vendors:
            if (vendor.total_document_count or 0) < MIN_OCCURRENCES_FOR_RECURRING:
                continue

            recent_docs = await self.documents.list_vendor_documents(
                org_id, vendor.id, limit=3
            )
            if len(recent_docs) < MIN_OCCURRENCES_FOR_RECURRING:
                continue

            amounts = [float(d.total_amount or 0) for d in recent_docs]
            # Same-amount recurrence (subscription signature): amounts
            # within 1% of each other across the recent documents.
            if not amounts or max(amounts) == 0:
                continue
            spread = (max(amounts) - min(amounts)) / max(amounts)
            if spread > 0.01:
                continue

            monthly_amount = amounts[0]
            total_monthly += monthly_amount

            last_seen = getattr(vendor, "last_seen", None)
            is_unused = False
            if last_seen:
                last_seen_date = last_seen.date() if hasattr(last_seen, "date") else last_seen
                if (now - last_seen_date).days > UNUSED_THRESHOLD_DAYS:
                    is_unused = True
                    unused.append(vendor.name)

            subscriptions.append(
                {
                    "vendor_id": str(vendor.id),
                    "vendor_name": vendor.name,
                    "monthly_amount": monthly_amount,
                    "is_unused": is_unused,
                }
            )

        return AnalyzerResult(
            name="subscription",
            data={
                "subscriptions": subscriptions,
                "total_monthly": round(total_monthly, 2),
                "unused": len(unused),
                "unused_vendor_names": unused,
            },
        )
