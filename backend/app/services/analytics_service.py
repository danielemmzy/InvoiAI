"""
============================================================
Analytics Service

Aggregates dashboard analytics.

No SQL.
Repositories only.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.repositories.document.document_repository import (
    DocumentRepository,
)
from app.repositories.document.vendor_repository import (
    VendorRepository,
)
from app.repositories.organization.organization_repository import (
    OrganizationRepository,
)


class AnalyticsService:
    """
    Dashboard analytics service.
    """

    def __init__(self) -> None:

        self.documents = DocumentRepository()
        self.vendors = VendorRepository()
        self.organizations = OrganizationRepository()

    # =========================================================
    # Dashboard
    # =========================================================

    async def dashboard(
        self,
        org_id: UUID,
    ) -> dict:

        return {
            "overview": await self.overview(org_id),
            "documents": await self.document_metrics(org_id),
            "vendors": await self.vendor_metrics(org_id),
            "risk": await self.risk_metrics(org_id),
            "trends": await self.trends(org_id),
            "organization": await self.organization_metrics(
                org_id
            ),
        }

    # =========================================================
    # Overview
    # =========================================================

    async def overview(
        self,
        org_id: UUID,
    ) -> dict:

        return {
            "documents": await self.documents.total_document_count(
                org_id
            ),
            "amount": await self.documents.total_document_amount(
                org_id
            ),
            "vendors": await self.vendors.vendor_count(
                org_id
            ),
            "processing": await self.documents.count_processing(
                org_id
            ),
        }

    # =========================================================
    # Documents
    # =========================================================

    async def document_metrics(
        self,
        org_id: UUID,
    ) -> dict:

        return {
            "approved": await self.documents.count_approved(
                org_id
            ),
            "rejected": await self.documents.count_rejected(
                org_id
            ),
            "failed": await self.documents.count_failed(
                org_id
            ),
            "needs_review": await self.documents.count_needs_review(
                org_id
            ),
            "completed": await self.documents.count_completed(
                org_id
            ),
        }

    # =========================================================
    # Vendors
    # =========================================================

    async def vendor_metrics(
        self,
        org_id: UUID,
    ) -> dict:

        return {
            "total": await self.vendors.vendor_count(
                org_id
            ),
            "preferred": await self.vendors.preferred_vendor_count(
                org_id
            ),
            "blocked": await self.vendors.blocked_vendor_count(
                org_id
            ),
            "new_this_month": await self.vendors.new_vendors_this_month(
                org_id
            ),
            "top_spend": await self.vendors.top_vendors_by_spend(
                org_id
            ),
            "top_documents": await self.vendors.top_vendors_by_documents(
                org_id
            ),
        }

    # =========================================================
    # Risk
    # =========================================================

    async def risk_metrics(
        self,
        org_id: UUID,
    ) -> dict:

        return {
            "distribution": await self.documents.risk_distribution(
                org_id
            ),
            "duplicates": await self.documents.duplicate_count(
                org_id
            ),
            "fraud_flags": await self.documents.fraud_flag_count(
                org_id
            ),
            "average_score": await self.documents.average_risk_score(
                org_id
            ),
            "high_risk_documents": await self.documents.high_risk_documents(
                org_id
            ),
            "high_risk_vendors": await self.vendors.highest_risk_vendors(
                org_id
            ),
        }

    # =========================================================
    # Trends
    # =========================================================

    async def trends(
        self,
        org_id: UUID,
    ) -> dict:

        return {
            "daily_documents": await self.documents.documents_per_day(
                org_id
            ),
            "monthly_documents": await self.documents.documents_per_month(
                org_id
            ),
            "monthly_spending": await self.documents.spending_per_month(
                org_id
            ),
        }

    # =========================================================
    # Organization
    # =========================================================

    async def organization_metrics(
        self,
        org_id: UUID,
    ) -> dict:

        return {
            "plan": await self.organizations.plan_usage(
                org_id
            ),
            "storage": await self.organizations.storage_usage(
                org_id
            ),
        }