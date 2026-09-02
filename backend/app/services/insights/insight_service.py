"""
============================================================
Insight Service

Flow 10 orchestrator: runs all 6 analyzers, feeds their output
to all 5 detectors, bulk-inserts any findings as Insight rows,
and alerts org owners when a critical-severity insight fires.

This is the file that workers/insight_worker.py imports —
previously it pointed at a module that did not exist at all,
which meant the worker crashed on its very first scheduled run.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.enum.notification import NotificationType
from app.repositories.insight.insight_repository import InsightRepository
from app.repositories.organization.member_repository import MemberRepository
from app.services.insights.analyzers.cashflow_analyzer import CashflowAnalyzer
from app.services.insights.analyzers.payable_analyzer import PayableAnalyzer
from app.services.insights.analyzers.receivable_analyzer import ReceivableAnalyzer
from app.services.insights.analyzers.spending_analyzer import SpendingAnalyzer
from app.services.insights.analyzers.subscription_analyzer import SubscriptionAnalyzer
from app.services.insights.analyzers.vendor_analyzer import VendorAnalyzer
from app.services.insights.detectors.cashflow_detector import CashflowDetector
from app.services.insights.detectors.duplicate_charge_detector import (
    DuplicateChargeDetector,
)
from app.services.insights.detectors.expense_anomaly_detector import (
    ExpenseAnomalyDetector,
)
from app.services.insights.detectors.overdue_detector import OverdueDetector
from app.services.insights.detectors.price_increase_detector import (
    PriceIncreaseDetector,
)
from app.services.notification.notification_service import NotificationService

INSIGHT_TTL_DAYS = 7


class InsightService:
    def __init__(
        self,
        *,
        insight_repository: InsightRepository | None = None,
        member_repository: MemberRepository | None = None,
        notification_service: NotificationService | None = None,
        cashflow_analyzer: CashflowAnalyzer | None = None,
        vendor_analyzer: VendorAnalyzer | None = None,
        receivable_analyzer: ReceivableAnalyzer | None = None,
        payable_analyzer: PayableAnalyzer | None = None,
        spending_analyzer: SpendingAnalyzer | None = None,
        subscription_analyzer: SubscriptionAnalyzer | None = None,
    ) -> None:
        self.insights = insight_repository or InsightRepository()
        self.members = member_repository or MemberRepository()
        self.notifications = notification_service or NotificationService()

        self.cashflow_analyzer = cashflow_analyzer or CashflowAnalyzer()
        self.vendor_analyzer = vendor_analyzer or VendorAnalyzer()
        self.receivable_analyzer = receivable_analyzer or ReceivableAnalyzer()
        self.payable_analyzer = payable_analyzer or PayableAnalyzer()
        self.spending_analyzer = spending_analyzer or SpendingAnalyzer()
        self.subscription_analyzer = subscription_analyzer or SubscriptionAnalyzer()

        self.overdue_detector = OverdueDetector()
        self.price_increase_detector = PriceIncreaseDetector()
        self.expense_anomaly_detector = ExpenseAnomalyDetector()
        self.cashflow_detector = CashflowDetector()
        self.duplicate_charge_detector = DuplicateChargeDetector()

    async def generate(self, org_id: UUID) -> list:
        """
        Runs every analyzer, then every detector, then bulk-writes
        any findings. Returns the created Insight rows.
        """

        cashflow_result = await self.cashflow_analyzer.run(org_id)
        vendor_result = await self.vendor_analyzer.run(org_id)
        receivable_result = await self.receivable_analyzer.run(org_id)
        payable_result = await self.payable_analyzer.run(org_id)
        spending_result = await self.spending_analyzer.run(org_id)
        subscription_result = await self.subscription_analyzer.run(org_id)

        findings = [
            self.overdue_detector.detect(receivable_result),
            self.price_increase_detector.detect(vendor_result),
            self.expense_anomaly_detector.detect(spending_result),
            self.cashflow_detector.detect(cashflow_result),
            self.duplicate_charge_detector.detect(subscription_result),
        ]

        # payable_result currently informs the copilot/dashboard
        # directly (GET /finance/... style reads) rather than a
        # dedicated detector — the flow doc doesn't define a
        # "payable_detector", only the 5 listed above.
        _ = payable_result

        findings = [f for f in findings if f is not None]

        if not findings:
            return []

        now = datetime.now(UTC)
        expires_at = now + timedelta(days=INSIGHT_TTL_DAYS)

        rows = [
            {
                "org_id": str(org_id),
                "insight_type": f["insight_type"].value,
                "severity": f["severity"].value,
                "title": f["title"],
                "description": f["description"],
                "data": f["data"],
                "recommended_action": f.get("recommended_action"),
                "is_read": False,
                "is_dismissed": False,
                "expires_at": expires_at.isoformat(),
            }
            for f in findings
        ]

        created = await self.insights.bulk_create(rows)

        critical = [f for f in findings if f["severity"].value == "critical"]
        if critical:
            await self._alert_owners(org_id, critical)

        return created

    async def _alert_owners(self, org_id: UUID, critical_findings: list[dict]) -> None:
        owner = await self.members.get_owner(org_id)
        if not owner:
            return

        owner_id = getattr(owner, "user_id", None) or getattr(owner, "id", None)
        if not owner_id:
            return

        titles = "; ".join(f["title"] for f in critical_findings)

        await self.notifications.send(
            user_id=owner_id,
            organization_id=org_id,
            type=NotificationType.INSIGHT_CRITICAL,
            title="InvoiAI found critical issues in your finances",
            message=titles,
            data={"findings": [f["title"] for f in critical_findings]},
        )

    async def list_active(self, org_id: UUID, limit: int = 50, offset: int = 0):
        return await self.insights.list_active_for_org(org_id, limit, offset)

    async def dismiss(self, insight_id: UUID, org_id: UUID):
        # Resource-level authorization: the insight must belong to the
        # authenticated user's active organization before mutation.
        insight = await self.insights.get(insight_id)
        if insight is None or insight.org_id != org_id:
            raise ValueError("Insight not found.")
        return await self.insights.dismiss(insight_id)
