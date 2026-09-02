"""
============================================================
Spending Analyzer

Flow 10 — "spending_analyzer.run(org_id) -> document_line_items
grouped by category, month-over-month, unusual_spikes = category
where MoM > 2 std deviations". Pure Python math. No LLM.

No dedicated line_item_repository exists yet (only
DocumentRepository.get_document_line_items(document_id) for a
single document) — this analyzer does its own two-step query
(documents in range -> their line items) via the Supabase
client already exposed on DocumentRepository.db, rather than
guessing at a repository method that isn't there.
============================================================
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repositories.document.document_repository import DocumentRepository
from app.services.insights.result import AnalyzerResult

SPIKE_STD_DEVIATIONS = 2.0


class SpendingAnalyzer:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self.documents = document_repository or DocumentRepository()

    async def run(self, org_id: UUID, months_back: int = 4) -> AnalyzerResult:
        monthly_totals = await self._category_totals_by_month(org_id, months_back)

        if not monthly_totals:
            return AnalyzerResult(name="spending", data={"unusual_spikes": []})

        categories = {
            cat
            for month_data in monthly_totals.values()
            for cat in month_data
        }

        months_sorted = sorted(monthly_totals.keys())
        current_month = months_sorted[-1]
        history_months = months_sorted[:-1]

        spikes = []
        for category in categories:
            history = [
                monthly_totals[m].get(category, 0.0) for m in history_months
            ]
            current = monthly_totals[current_month].get(category, 0.0)

            if len(history) < 2 or current <= 0:
                continue

            mean = statistics.mean(history)
            stdev = statistics.pstdev(history) if len(history) > 1 else 0.0

            if stdev == 0:
                continue

            deviations = (current - mean) / stdev
            if deviations >= SPIKE_STD_DEVIATIONS:
                increase_pct = round(((current - mean) / mean) * 100, 1) if mean else 0.0
                spikes.append(
                    {
                        "category": category,
                        "current_month_total": current,
                        "average_total": round(mean, 2),
                        "increase_pct": increase_pct,
                        "std_deviations": round(deviations, 1),
                    }
                )

        spikes.sort(key=lambda x: x["std_deviations"], reverse=True)

        return AnalyzerResult(
            name="spending",
            data={
                "unusual_spikes": spikes,
                "top_spike": spikes[0] if spikes else None,
            },
        )

    async def _category_totals_by_month(
        self,
        org_id: UUID,
        months_back: int,
    ) -> dict[str, dict[str, float]]:
        today = datetime.now(UTC).date()
        window_start = today - timedelta(days=30 * (months_back + 1))

        docs = await self.documents.list_documents_for_spending(
            org_id=org_id,
            start_date=window_start.isoformat(),
        )
        if not docs:
            return {}

        doc_month_by_id = {
            row["id"]: str(row.get("document_date") or "")[:7]
            for row in docs
            if row.get("document_date")
        }
        line_items = await self.documents.list_line_items_for_documents(
            document_ids=list(doc_month_by_id),
        )

        totals: dict[str, dict[str, float]] = {}
        for item in line_items:
            month = doc_month_by_id.get(item.get("document_id"))
            category = item.get("category") or "uncategorized"
            amount = float(item.get("amount") or 0)
            if not month:
                continue
            totals.setdefault(month, {})
            totals[month][category] = totals[month].get(category, 0.0) + amount
        return totals

