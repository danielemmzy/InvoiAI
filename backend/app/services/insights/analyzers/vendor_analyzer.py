"""
============================================================
Vendor Analyzer

Flow 10 — "vendor_analyzer.run(org_id) -> vendors.avg_amount vs
latest invoice per vendor, price_increase_pct". Pure Python
math. No LLM.

Also backs the Copilot's get_vendor_price_changes tool
(services/ai/tools/business_tools.py) and Flow 7's example
query "Which vendor increased prices most this month?" — same
analyzer, two callers, one source of truth for the numbers.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.repositories.document.document_repository import DocumentRepository
from app.repositories.document.vendor_repository import VendorRepository
from app.services.insights.result import AnalyzerResult


class VendorAnalyzer:
    def __init__(
        self,
        vendor_repository: VendorRepository | None = None,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self.vendors = vendor_repository or VendorRepository()
        self.documents = document_repository or DocumentRepository()

    async def run(self, org_id: UUID, top_n: int = 10) -> AnalyzerResult:
        top_vendors = await self.vendors.top_vendors_by_spend(org_id, limit=top_n)

        increases: list[dict] = []

        for vendor in top_vendors:
            avg = float(vendor.average_spend or 0)
            if avg <= 0:
                continue

            recent_docs = await self.documents.list_vendor_documents(
                org_id, vendor.id, limit=1, offset=0
            )
            if not recent_docs:
                continue

            latest_amount = float(recent_docs[0].total_amount or 0)
            if latest_amount <= 0:
                continue

            increase_pct = round(((latest_amount - avg) / avg) * 100, 1)
            std_deviations = (
                round((latest_amount - avg) / float(vendor.stddev_spend), 1)
                if getattr(vendor, "stddev_spend", 0)
                else 0.0
            )

            increases.append(
                {
                    "vendor_id": str(vendor.id),
                    "vendor_name": vendor.name,
                    "avg_amount": avg,
                    "latest_amount": latest_amount,
                    "increase_pct": increase_pct,
                    "std_deviations": std_deviations,
                    "invoice_count": vendor.total_document_count,
                }
            )

        increases.sort(key=lambda x: x["increase_pct"], reverse=True)

        return AnalyzerResult(
            name="vendor",
            data={
                "increases": increases,
                "top_increase": increases[0] if increases else None,
            },
        )
