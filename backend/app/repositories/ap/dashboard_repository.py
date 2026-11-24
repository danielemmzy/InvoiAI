from __future__ import annotations

from datetime import date
from uuid import UUID

from app.core.db import execute
from app.core.supabase import get_supabase


class APDashboardRepository:
    """
    Persistence boundary for AP dashboard read models.

    Dashboard data is a read projection assembled from:

        documents
        vendors
        document_analyses
        organizations

    Business calculations remain in APDashboardService.

    Every read goes through ``execute`` so the synchronous Supabase client is
    not called directly on the event loop thread.
    """

    def __init__(self, db=None):
        self.db = db or get_supabase()

    # ============================================================
    # Invoice base query
    # ============================================================

    def invoice_query(self, org_id: UUID):
        return (
            self.db
            .table("documents")
            .select(
                """
                id,
                org_id,
                vendor_id,
                vendor_name,
                document_number,
                document_date,
                due_date,
                currency,
                total_amount,
                amount_paid,
                amount_due,
                payment_terms,
                payment_method,
                ap_enabled,
                ap_status,
                match_status,
                gl_coding_status,
                is_archived,
                created_at
                """,
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq("document_type", "invoice")
            .eq("ap_enabled", True)
            .eq("is_archived", False)
        )

    # ============================================================
    # Paginated invoices
    # ============================================================

    async def list_invoices(
        self,
        org_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        vendor_id: UUID | None = None,
        currency: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:

        query = self.invoice_query(org_id)

        if date_from:
            query = query.gte(
                "document_date",
                date_from.isoformat(),
            )

        if date_to:
            query = query.lte(
                "document_date",
                date_to.isoformat(),
            )

        if vendor_id:
            query = query.eq(
                "vendor_id",
                str(vendor_id),
            )

        if currency:
            query = query.eq(
                "currency",
                currency.upper(),
            )

        response = await execute(
            query
            .order("document_date", desc=True)
            .order("created_at", desc=True)
            .range(
                offset,
                offset + limit - 1,
            )
        )

        return (
            response.data or [],
            response.count or 0,
        )

    # ============================================================
    # Dashboard projection
    # ============================================================

    async def list_invoice_projection(
        self,
        org_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        currency: str | None = None,
    ) -> list[dict]:

        query = self.invoice_query(org_id)

        if date_from:
            query = query.gte(
                "document_date",
                date_from.isoformat(),
            )

        if date_to:
            query = query.lte(
                "document_date",
                date_to.isoformat(),
            )

        if currency:
            query = query.eq(
                "currency",
                currency.upper(),
            )

        response = await execute(
            query
            .order("document_date", desc=False)
            .order("created_at", desc=False)
        )

        return response.data or []

    # ============================================================
    # Vendors
    # ============================================================

    async def get_vendors(
        self,
        org_id: UUID,
        vendor_ids: list[UUID] | None = None,
    ) -> list[dict]:

        query = (
            self.db
            .table("vendors")
            .select(
                """
                id,
                name,
                risk_score,
                risk_level,
                is_active,
                is_blocked
                """
            )
            .eq("org_id", str(org_id))
        )

        if vendor_ids:
            query = query.in_(
                "id",
                [str(vendor_id) for vendor_id in vendor_ids],
            )

        response = await execute(query)

        return response.data or []

    async def count_vendors(
        self,
        org_id: UUID,
    ) -> int:

        response = await execute(
            self.db
            .table("vendors")
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq("is_blocked", False)
        )

        return response.count or 0

    # ============================================================
    # Document analyses
    # ============================================================

    async def get_analyses(
        self,
        org_id: UUID,
        document_ids: list[UUID],
    ) -> list[dict]:

        if not document_ids:
            return []

        response = await execute(
            self.db
            .table("document_analyses")
            .select(
                """
                document_id,
                health_score,
                risk_level,
                created_at
                """
            )
            .eq("org_id", str(org_id))
            .in_(
                "document_id",
                [str(document_id) for document_id in document_ids],
            )
            .order(
                "created_at",
                desc=True,
            )
        )

        return response.data or []

    # ============================================================
    # Organization
    # ============================================================

    async def get_organization_currency(
        self,
        org_id: UUID,
    ) -> str:

        response = await execute(
            self.db
            .table("organizations")
            .select("currency")
            .eq("id", str(org_id))
            .limit(1)
        )

        rows = response.data or []

        if not rows:
            return "USD"

        return str(
            rows[0].get("currency") or "USD"
        ).upper()
