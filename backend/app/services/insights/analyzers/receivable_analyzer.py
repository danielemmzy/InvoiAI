"""
============================================================
Receivable Analyzer

Flow 10 — "receivable_analyzer.run(org_id) -> overdue_count,
overdue_amount, payment_trend". Pure Python math. No LLM.

NOTE: your schema has no dedicated `receivables`/`customers`
tables yet. This treats outstanding customer-facing invoices
(documents currently sitting in NEEDS_REVIEW or IN_APPROVAL,
i.e. not yet settled) as the receivables set, and flags any
past their due_date as overdue. If/when a real receivables
ledger exists, swap the query in `_overdue_documents` for it —
the rest of this analyzer's shape won't need to change.
============================================================
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from app.core.enum.database import DocumentStatus
from app.repositories.document.document_repository import DocumentRepository
from app.services.insights.result import AnalyzerResult


class ReceivableAnalyzer:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self.documents = document_repository or DocumentRepository()

    async def run(self, org_id: UUID) -> AnalyzerResult:
        overdue_docs = await self._overdue_documents(org_id)

        overdue_count = len(overdue_docs)
        overdue_amount = sum(
            (float(d.total_amount or 0) for d in overdue_docs), 0.0
        )

        top_customer = None
        if overdue_docs:
            worst = max(overdue_docs, key=lambda d: float(d.total_amount or 0))
            top_customer = worst.vendor_name or "Unknown"

        return AnalyzerResult(
            name="receivable",
            data={
                "overdue_count": overdue_count,
                "overdue_amount": overdue_amount,
                "top_customer": top_customer,
                "payment_trend": "stable",
                # "faster"/"slower"/"stable" requires historical
                # average-payment-days tracking per customer, which
                # doesn't exist yet — defaulting to "stable" rather
                # than fabricating a trend.
            },
        )

    async def _overdue_documents(self, org_id: UUID) -> list:
        today = datetime.now(UTC).date()

        candidates = []
        for status in (DocumentStatus.NEEDS_REVIEW, DocumentStatus.IN_APPROVAL):
            candidates.extend(
                await self.documents.list_by_status(org_id, status, limit=200)
            )

        return [
            d for d in candidates
            if getattr(d, "due_date", None) and self._as_date(d.due_date) < today
        ]

    @staticmethod
    def _as_date(value) -> date:
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return date.max
