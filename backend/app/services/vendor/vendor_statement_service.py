from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.core.supabase import get_supabase
from app.repositories.ap.dashboard_repository import APDashboardRepository
from app.services.fx.fx_service import FXService


class VendorStatementService:
    """Builds the tenant-scoped vendor statement read model used by the UI."""

    def __init__(self, db=None, dashboard: APDashboardRepository | None = None, fx: FXService | None = None):
        self.db = db or get_supabase()
        self.dashboard = dashboard or APDashboardRepository(self.db)
        self.fx = fx or FXService()

    async def get(self, org_id: UUID, vendor_id: UUID) -> dict:
        vendor_rows = (
            self.db.table("vendors")
            .select("id,name,risk_score,risk_level,fraud_flags,currencies_used,typical_currency")
            .eq("org_id", str(org_id)).eq("id", str(vendor_id)).limit(1).execute().data or []
        )
        if not vendor_rows:
            raise ValueError("Vendor not found.")
        vendor = vendor_rows[0]

        invoices = self.dashboard.list_invoice_projection(org_id, vendor_id=vendor_id) or []
        payments = (
            self.db.table("payments")
            .select("id,payment_number,amount,currency,payment_date,status,document_id")
            .eq("org_id", str(org_id)).eq("vendor_id", str(vendor_id))
            .order("payment_date", desc=True).limit(500).execute().data or []
        )

        reporting_currency = str(
            vendor.get("typical_currency")
            or (vendor.get("currencies_used") or [None])[0]
            or self.dashboard.get_organization_currency(org_id)
            or "USD"
        ).upper()

        today = date.today()
        date_candidates = []
        for row in invoices:
            raw = row.get("document_date") or row.get("created_at")
            if raw:
                try:
                    date_candidates.append(date.fromisoformat(str(raw)[:10]))
                except ValueError:
                    pass
        for row in payments:
            raw = row.get("payment_date")
            if raw:
                try:
                    date_candidates.append(date.fromisoformat(str(raw)[:10]))
                except ValueError:
                    pass
        date_from = min(date_candidates) if date_candidates else today
        date_to = today
        invoices = await self.fx.convert_rows(
            invoices,
            reporting_currency,
            date_from=date_from,
            date_to=date_to,
        ) if invoices else []

        payment_rows = [
            {
                "id": p.get("id"),
                "document_date": p.get("payment_date") or p.get("created_at") or today.isoformat(),
                "created_at": p.get("payment_date") or today.isoformat(),
                "currency": p.get("currency") or reporting_currency,
                "total_amount": p.get("amount") or 0,
                "amount_paid": p.get("amount") or 0,
                "amount_due": 0,
            }
            for p in payments
        ]
        payment_rows = await self.fx.convert_rows(
            payment_rows, reporting_currency, date_from=date_from, date_to=date_to
        ) if payment_rows else []

        total_purchases = sum((Decimal(str(r.get("reporting_total_amount") or 0)) for r in invoices), Decimal("0"))
        total_payments = sum((Decimal(str(r.get("reporting_total_amount") or 0)) for r in payment_rows), Decimal("0"))

        open_invoices = []
        balance_by_status: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        trend: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"billed": Decimal("0"), "paid": Decimal("0")})
        overdue_days: list[int] = []

        for row in invoices:
            amount = Decimal(str(row.get("reporting_total_amount") or 0))
            paid = Decimal(str(row.get("reporting_paid_amount") or 0))
            balance = max(Decimal(str(row.get("reporting_balance_due") or 0)), Decimal("0"))
            due = row.get("due_date")
            status = str(row.get("ap_status") or "").lower() or "open"
            if balance <= 0 and amount > 0:
                status = "paid"
            elif due:
                try:
                    if date.fromisoformat(str(due)[:10]) < today:
                        status = "overdue"
                        overdue_days.append(max(0, (today - date.fromisoformat(str(due)[:10])).days))
                except ValueError:
                    pass
            if balance > 0:
                open_invoices.append(row)
            balance_by_status[status] += balance
            month = str(row.get("document_date") or row.get("created_at") or today)[:7]
            trend[month]["billed"] += amount
            trend[month]["paid"] += paid

        months = []
        cursor = date(today.year, today.month, 1)
        for _ in range(12):
            key = cursor.strftime("%Y-%m")
            months.append({
                "month": key,
                "billed": float(trend[key]["billed"]),
                "paid": float(trend[key]["paid"]),
            })
            cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

        recent = sorted(invoices, key=lambda r: str(r.get("document_date") or ""), reverse=True)[:10]
        recent_invoices = [{
            "id": str(r["id"]),
            "vendor_id": str(r.get("vendor_id") or vendor_id),
            "vendor_name": vendor.get("name") or "Unknown vendor",
            "invoice_number": r.get("document_number"),
            "amount": float(r.get("total_amount") or 0),
            "currency": str(r.get("currency") or reporting_currency).upper(),
            "status": r.get("ap_status") or ("paid" if Decimal(str(r.get("amount_due") or 0)) <= 0 else "open"),
            "priority": "low",
            "tags": [],
            "issue_date": r.get("document_date"),
            "due_date": r.get("due_date"),
            "document_id": str(r["id"]),
        } for r in recent]

        return {
            "vendor_id": str(vendor_id),
            "vendor_name": vendor.get("name") or "Unknown vendor",
            "currency": reporting_currency,
            "credit_limit": None,
            "total_purchases": float(total_purchases),
            "total_payments": float(total_payments),
            "total_balance": float(max(total_purchases - total_payments, Decimal("0"))),
            "open_invoices": len(open_invoices),
            "avg_overdue_days": round(sum(overdue_days) / len(overdue_days)) if overdue_days else 0,
            "risk_score": int(vendor.get("risk_score") or 0),
            "risk_level": vendor.get("risk_level") or "low",
            "fraud_flags": int(vendor.get("fraud_flags") or 0),
            "trend": months,
            "balance_by_status": [{"status": k, "amount": float(v)} for k, v in sorted(balance_by_status.items())],
            "recent_invoices": recent_invoices,
        }
