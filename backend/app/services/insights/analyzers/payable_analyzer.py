"""
============================================================
Payable Analyzer

Flow 10 — "payable_analyzer.run(org_id) -> documents WHERE
due_date < now() + 7 days -> upcoming_due, total". Pure Python
math. No LLM.
============================================================
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.core.enum.database import DocumentStatus
from app.repositories.document.document_repository import DocumentRepository
from app.services.insights.result import AnalyzerResult


class PayableAnalyzer:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self.documents = document_repository or DocumentRepository()

    async def run(self, org_id: UUID, horizon_days: int = 7) -> AnalyzerResult:
        today = datetime.now(UTC).date()
        horizon = today + timedelta(days=horizon_days)

        candidates = []
        for status in (
            DocumentStatus.APPROVED,
            DocumentStatus.NEEDS_REVIEW,
            DocumentStatus.IN_APPROVAL,
        ):
            candidates.extend(
                await self.documents.list_by_status(org_id, status, limit=200)
            )

        upcoming = [
            d for d in candidates
            if getattr(d, "due_date", None)
            and today <= self._as_date(d.due_date) <= horizon
        ]

        total = sum((float(d.total_amount or 0) for d in upcoming), 0.0)

        return AnalyzerResult(
            name="payable",
            data={
                "upcoming_due": len(upcoming),
                "total": total,
                "horizon_days": horizon_days,
                "documents": [
                    {
                        "document_id": str(d.id),
                        "vendor_name": d.vendor_name,
                        "amount": float(d.total_amount or 0),
                        "due_date": str(d.due_date),
                    }
                    for d in upcoming
                ],
            },
        )

    @staticmethod
    def _as_date(value) -> date:
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return date.max
