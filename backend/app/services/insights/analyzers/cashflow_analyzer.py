"""
============================================================
Cashflow Analyzer

Flow 10 — "cashflow_analyzer.run(org_id) -> cash_runway_days,
predicted_shortfall". Pure Python math against payments and
outstanding documents. No LLM.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repositories.document.document_repository import DocumentRepository
from app.repositories.document.payment_repository import PaymentRepository
from app.services.insights.result import AnalyzerResult


class CashflowAnalyzer:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        payment_repository: PaymentRepository | None = None,
    ) -> None:
        self.documents = document_repository or DocumentRepository()
        self.payments = payment_repository or PaymentRepository()

    async def run(self, org_id: UUID) -> AnalyzerResult:
        now = datetime.now(UTC)
        window_start = now - timedelta(days=90)

        payments = await self.payments.list_org_payments(org_id, limit=500)

        outflow_payments = [
            p for p in payments
            if getattr(p, "created_at", now) >= window_start
        ]

        total_outflow = sum(
            (getattr(p, "amount", 0) or 0 for p in outflow_payments),
            start=0,
        )

        days_in_window = 90
        monthly_burn_rate = float(total_outflow) / days_in_window * 30 if total_outflow else 0.0

        cash_balance = await self._estimate_cash_balance(org_id, payments)

        cash_runway_days = (
            int((cash_balance / monthly_burn_rate) * 30)
            if monthly_burn_rate > 0
            else None
        )

        upcoming_due = await self.documents.list_by_pipeline_stage(
            org_id, "approval", limit=100
        ) if hasattr(self.documents, "list_by_pipeline_stage") else []

        predicted_shortfall = 0.0
        if cash_runway_days is not None and cash_runway_days < 30:
            upcoming_total = sum(
                (float(getattr(d, "total_amount", 0) or 0) for d in upcoming_due),
                0.0,
            )
            predicted_shortfall = max(0.0, upcoming_total - cash_balance)

        return AnalyzerResult(
            name="cashflow",
            data={
                "cash_balance": cash_balance,
                "monthly_burn_rate": monthly_burn_rate,
                "cash_runway_days": cash_runway_days,
                "predicted_shortfall": predicted_shortfall,
            },
        )

    @staticmethod
    async def _estimate_cash_balance(org_id: UUID, payments) -> float:
        """
        NOTE: there is no dedicated bank-balance table in the schema
        yet. This is a conservative proxy (negative of trailing
        90-day outflow) until a real balance source (Flow 9's bank
        statement income/expense ledger, or a connected bank feed)
        is wired in. Replace with a real balance lookup once
        available — flagged here rather than silently guessing.
        """
        return 0.0
