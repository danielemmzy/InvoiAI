from __future__ import annotations

import asyncio
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from app.repositories.ap.dashboard_repository import APDashboardRepository
from app.services.fx.fx_service import FXRateUnavailable, FXService


ZERO = Decimal("0")


class APDashboardService:
    """Builds tenant-scoped AP dashboard read models."""

    OPEN_STATUSES = {
        "received", "extracting", "validating", "matching", "coding",
        "awaiting_approval", "approved", "syncing_to_erp", "payment_ready",
        "match_exception", "coding_exception", "on_hold",
    }

    def __init__(
        self,
        repository: APDashboardRepository | None = None,
        fx_service: FXService | None = None,
    ):
        self.repository = repository or APDashboardRepository()
        self.fx_service = fx_service or FXService()

    @staticmethod
    def _money(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return ZERO

    @staticmethod
    def _round(value: Decimal) -> float:
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _month_start(value: date) -> date:
        return value.replace(day=1)

    @staticmethod
    def _add_months(value: date, months: int) -> date:
        month = value.month - 1 + months
        year = value.year + month // 12
        month = month % 12 + 1
        return date(year, month, 1)

    @staticmethod
    def _status(row: dict, today: date | None = None) -> str:
        today = today or date.today()
        # Accounting truth comes from the canonical document columns.
        # Do not read payment_status/paid_amount/balance_due from raw DB rows.
        paid = APDashboardService._money(row.get("amount_paid"))
        balance = APDashboardService._money(row.get("amount_due"))
        total = APDashboardService._money(row.get("total_amount"))

        # Derive payment state from accounting amounts first.
        if balance <= ZERO and (total > ZERO or paid > ZERO):
            status = "paid"
        elif paid > ZERO:
            status = "partially_paid"
        else:
            due = row.get("due_date")
            if due and balance > ZERO:
                try:
                    due_date = date.fromisoformat(str(due)[:10])
                    status = "overdue" if due_date < today else "open"
                except ValueError:
                    status = "open"
            else:
                status = "open"

        # AP workflow state is a separate concern and overrides the
        # derived payment state where the workflow has an explicit state.
        ap_status = str(row.get("ap_status") or "").lower()

        if ap_status == "rejected":
            status = "rejected"
        elif ap_status == "match_exception":
            status = "match_exception"
        elif ap_status == "coding_exception":
            status = "coding_exception"
        elif ap_status == "awaiting_approval":
            status = "awaiting_approval"
        elif ap_status == "approved":
            status = "approved"
        elif ap_status == "payment_ready":
            status = "payment_ready"
        elif ap_status in {"paid", "reconciled"}:
            status = "paid"

        return status

    @classmethod
    def _priority(cls, row: dict, today: date | None = None) -> str:
        today = today or date.today()
        status = cls._status(row, today)
        if status == "overdue":
            due = row.get("due_date")
            days = 0
            if due:
                try:
                    days = max(0, (today - date.fromisoformat(str(due)[:10])).days)
                except ValueError:
                    pass
            if days >= 60:
                return "urgent"
            if days >= 30:
                return "high"
            return "medium"

        if status in {"match_exception", "coding_exception"}:
            return "high"
        if status == "awaiting_approval":
            return "medium"
        return "low"

    @staticmethod
    def _tags(row: dict, status: str) -> list[str]:
        tags: list[str] = []
        if status == "overdue":
            tags.append("overdue")
        if row.get("match_status") == "exception" or status == "match_exception":
            tags.append("match-exception")
        if row.get("gl_coding_status") == "needs_review" or status == "coding_exception":
            tags.append("coding-exception")
        if status == "payment_ready":
            tags.append("payment-ready")
        if status == "paid":
            tags.append("paid")
        return tags

    @staticmethod
    def _matches(row: dict, filters) -> bool:
        if filters.vendor_id and str(row.get("vendor_id")) != str(filters.vendor_id):
            return False
        if filters.status and row["computed_status"] != filters.status:
            return False
        if filters.priority and row["computed_priority"] != filters.priority:
            return False
        if filters.search:
            search = filters.search.strip().lower()
            haystack = f"{row.get('vendor_name') or ''} {row.get('document_number') or ''}".lower()
            if search not in haystack:
                return False
        return True

    async def _enrich(self, org_id: UUID, rows: list[dict]) -> tuple[list[dict], dict[str, dict]]:
        ids = [UUID(str(row["id"])) for row in rows if row.get("id")]

        vendor_ids = []
        seen: set[str] = set()
        for row in rows:
            if row.get("vendor_id") and str(row["vendor_id"]) not in seen:
                seen.add(str(row["vendor_id"]))
                vendor_ids.append(UUID(str(row["vendor_id"])))

        # Analyses and vendors are independent reads; fetch them together so
        # enrichment costs one round-trip worth of latency instead of two.
        analyses, vendors = await asyncio.gather(
            self.repository.get_analyses(org_id, ids),
            self.repository.get_vendors(org_id, vendor_ids),
        )
        latest: dict[str, dict] = {}
        for analysis in analyses:
            key = str(analysis.get("document_id"))
            latest.setdefault(key, analysis)

        vendor_map = {str(v["id"]): v for v in vendors}

        enriched: list[dict] = []
        today = date.today()
        for row in rows:
            item = dict(row)
            vendor = vendor_map.get(str(row.get("vendor_id")), {})
            analysis = latest.get(str(row.get("id")), {})
            status = self._status(row, today)
            item["computed_status"] = status
            item["computed_priority"] = self._priority(row, today)
            item["tags"] = self._tags(row, status)
            item["health_score"] = analysis.get("health_score")
            item["risk_level"] = analysis.get("risk_level") or vendor.get("risk_level")
            item["vendor_name"] = row.get("vendor_name") or vendor.get("name") or "Unknown vendor"
            item["vendor_risk_score"] = vendor.get("risk_score") or 0
            item["vendor_risk_level"] = vendor.get("risk_level") or "low"
            enriched.append(item)
        return enriched, vendor_map

    async def _with_reporting_currency(
        self,
        rows: list[dict],
        filters,
        reporting_currency: str,
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        try:
            return await self.fx_service.convert_rows(
                rows,
                reporting_currency,
                date_from=date_from,
                date_to=date_to,
            )
        except FXRateUnavailable:
            raise

    async def list_invoices(self, org_id: UUID, filters, limit: int, offset: int) -> dict:
        org_currency = await self.repository.get_organization_currency(org_id)
        reporting_currency = (filters.reporting_currency or org_currency).upper()
        today = date.today()
        date_from = filters.date_from or self._add_months(self._month_start(today), -11)
        date_to = filters.date_to or today

        rows, _ = await self.repository.list_invoices(
            org_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            vendor_id=filters.vendor_id,
            currency=filters.currency,
            limit=1000,
            offset=0,
        )
        rows, _vendors = await self._enrich(org_id, rows)
        filtered = [row for row in rows if self._matches(row, filters)]

        # Keep the original invoice currency/amount intact while also exposing
        # a reporting amount when a reporting currency is selected.
        filtered = await self._with_reporting_currency(
            filtered, filters, reporting_currency, date_from, date_to
        )

        total = len(filtered)
        page = filtered[offset : offset + limit]
        items = [
            {
                "id": str(row["id"]),
                "vendor_id": str(row["vendor_id"]) if row.get("vendor_id") else "",
                "vendor_name": row["vendor_name"],
                "invoice_number": row.get("document_number"),
                "amount": self._round(self._money(row.get("total_amount"))),
                "currency": str(row.get("currency") or "USD").upper(),
                "reporting_amount": self._round(self._money(row.get("reporting_total_amount"))),
                "reporting_currency": reporting_currency,
                "fx_rate": self._round(self._money(row.get("fx_rate"))) if row.get("fx_rate") is not None else None,
                "fx_rate_date": row.get("fx_rate_date"),
                "status": row["computed_status"],
                "priority": row["computed_priority"],
                "tags": row["tags"],
                "issue_date": row.get("document_date"),
                "due_date": row.get("due_date"),
                "health_score": row.get("health_score"),
                "risk_level": row.get("risk_level"),
                "document_id": str(row["id"]),
            }
            for row in page
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def summary(self, org_id: UUID, filters) -> dict:
        org_currency = await self.repository.get_organization_currency(org_id)
        reporting_currency = (filters.reporting_currency or org_currency).upper()

        today = date.today()
        default_from = self._add_months(self._month_start(today), -11)
        date_from = filters.date_from or default_from
        date_to = filters.date_to or today

        # currency remains the transaction-currency filter. Reporting currency
        # is separate so selecting NGN does not hide USD/EUR invoices.
        rows = await self.repository.list_invoice_projection(
            org_id,
            date_from=date_from,
            date_to=date_to,
            currency=filters.currency,
        )
        rows, vendor_map = await self._enrich(org_id, rows)
        rows = [row for row in rows if self._matches(row, filters)]
        rows = await self._with_reporting_currency(
            rows, filters, reporting_currency, date_from, date_to
        )

        total = ZERO
        paid = ZERO
        open_amount = ZERO
        overdue = ZERO
        open_vendor_ids: set[str] = set()
        month_data: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"billed": ZERO, "paid": ZERO, "open": ZERO})
        currency_data: dict[str, Decimal] = defaultdict(lambda: ZERO)

        for row in rows:
            amount = self._money(row.get("reporting_total_amount"))
            paid_amount = min(max(self._money(row.get("reporting_paid_amount")), ZERO), max(amount, ZERO))
            balance = self._money(row.get("reporting_balance_due"))
            if balance == ZERO and amount > ZERO:
                balance = max(amount - paid_amount, ZERO)

            status = row["computed_status"]
            total += amount
            paid += paid_amount
            if status != "paid" and status != "rejected":
                open_amount += max(balance, ZERO)
                if row.get("vendor_id"):
                    open_vendor_ids.add(str(row["vendor_id"]))
            if status == "overdue":
                overdue += max(balance, ZERO)

            source_currency = str(row.get("currency") or reporting_currency).upper()
            currency_data[source_currency] += self._money(row.get("total_amount"))

            raw_month = row.get("document_date") or row.get("created_at")
            if raw_month:
                month = str(raw_month)[:7]
                month_data[month]["billed"] += amount
                month_data[month]["paid"] += paid_amount
                month_data[month]["open"] += max(balance, ZERO)

        months = []
        cursor = self._month_start(date_from)
        end = self._month_start(date_to)
        while cursor <= end:
            key = cursor.strftime("%Y-%m")
            data = month_data[key]
            months.append({"month": key, "billed": self._round(data["billed"]), "paid": self._round(data["paid"])})
            cursor = self._add_months(cursor, 1)

        turnover_trend = []
        for month in months:
            billed = Decimal(str(month["billed"]))
            open_balance = month_data[month["month"]]["open"]
            days = (open_balance / billed * Decimal("30")) if billed > ZERO else ZERO
            turnover_trend.append({"month": month["month"], "days": self._round(days)})

        billed_total = sum((month_data[k]["billed"] for k in month_data), ZERO)
        avg_monthly_billed = billed_total / Decimal(max(len(months), 1))
        turnover_days = (open_amount / avg_monthly_billed * Decimal("30")) if avg_monthly_billed > ZERO else ZERO

        total_vendors = await self.repository.count_vendors(org_id)

        return {
            "total_vendors": total_vendors,
            "open_vendors": len(open_vendor_ids),
            "total_invoices": len(rows),
            "open_invoices": sum(1 for r in rows if r["computed_status"] not in {"paid", "rejected"}),
            "total_amount": self._round(total),
            "total_paid": self._round(paid),
            "open_amount": self._round(open_amount),
            "overdue_amount": self._round(overdue),
            "currency": reporting_currency,
            "payables_by_month": months,
            "payable_turnover_days": self._round(turnover_days),
            "payable_turnover_trend": turnover_trend,
            "by_currency": [
                {"currency": currency, "amount": self._round(amount)}
                for currency, amount in sorted(currency_data.items())
            ],
        }

    async def top_vendors(self, org_id: UUID, filters) -> list[dict]:
        org_currency = await self.repository.get_organization_currency(org_id)
        reporting_currency = (filters.reporting_currency or org_currency).upper()
        today = date.today()
        date_from = filters.date_from or self._add_months(self._month_start(today), -11)
        date_to = filters.date_to or today
        rows = await self.repository.list_invoice_projection(
            org_id,
            date_from=date_from,
            date_to=date_to,
            currency=filters.currency,
        )
        rows, vendor_map = await self._enrich(org_id, rows)
        rows = [row for row in rows if self._matches(row, filters)]
        rows = await self._with_reporting_currency(rows, filters, reporting_currency, date_from, date_to)

        aggregate: dict[str, dict] = {}
        for row in rows:
            status = row["computed_status"]
            if status in {"paid", "rejected"}:
                continue
            vendor_id = str(row.get("vendor_id") or "")
            if not vendor_id:
                continue
            balance = self._money(row.get("reporting_balance_due"))
            if balance <= ZERO:
                balance = max(self._money(row.get("reporting_total_amount")) - self._money(row.get("reporting_paid_amount")), ZERO)
            entry = aggregate.setdefault(vendor_id, {"current": ZERO, "overdue": ZERO})
            entry["current"] += balance
            if status == "overdue":
                entry["overdue"] += balance

        result = []
        for vendor_id, values in aggregate.items():
            vendor = vendor_map.get(vendor_id, {})
            result.append({
                "vendor_id": vendor_id,
                "vendor_name": vendor.get("name") or "Unknown vendor",
                "current_balance": self._round(values["current"]),
                "overdue_balance": self._round(values["overdue"]),
                "currency": reporting_currency,
                "risk_score": int(vendor.get("risk_score") or 0),
                "risk_level": vendor.get("risk_level") or "low",
            })
        return sorted(result, key=lambda x: (x["current_balance"], x["overdue_balance"]), reverse=True)[:10]

    async def aging(self, org_id: UUID, filters) -> dict:
        currency = (filters.reporting_currency or await self.repository.get_organization_currency(org_id)).upper()
        today = date.today()
        date_from = filters.date_from or self._add_months(self._month_start(today), -11)
        date_to = filters.date_to or today
        rows = await self.repository.list_invoice_projection(
            org_id,
            date_from=date_from,
            date_to=date_to,
            currency=filters.currency,
        )
        rows, vendor_map = await self._enrich(org_id, rows)
        rows = await self._with_reporting_currency(rows, filters, currency, date_from, date_to)
        today = date.today()

        bucket_defs = [
            ("current", "Current"),
            ("1_30", "1–30 days"),
            ("31_60", "31–60 days"),
            ("61_90", "61–90 days"),
            ("90_plus", "90+ days"),
        ]
        buckets = {key: {"amount": ZERO, "invoice_count": 0} for key, _ in bucket_defs}
        vendor_rows: dict[str, dict[str, Decimal]] = defaultdict(lambda: {k: ZERO for k, _ in bucket_defs})

        for row in rows:
            if not self._matches(row, filters):
                continue
            if row["computed_status"] in {"paid", "rejected"}:
                continue
            balance = self._money(row.get("reporting_balance_due"))
            if balance <= ZERO:
                balance = max(self._money(row.get("reporting_total_amount")) - self._money(row.get("reporting_paid_amount")), ZERO)
            if balance <= ZERO:
                continue

            due = row.get("due_date")
            days_overdue = 0
            if due:
                try:
                    days_overdue = max(0, (today - date.fromisoformat(str(due)[:10])).days)
                except ValueError:
                    days_overdue = 0

            if days_overdue == 0:
                key = "current"
            elif days_overdue <= 30:
                key = "1_30"
            elif days_overdue <= 60:
                key = "31_60"
            elif days_overdue <= 90:
                key = "61_90"
            else:
                key = "90_plus"

            buckets[key]["amount"] += balance
            buckets[key]["invoice_count"] += 1
            vendor_id = str(row.get("vendor_id") or "")
            if vendor_id:
                vendor_rows[vendor_id][key] += balance

        bucket_response = [
            {
                "bucket": key,
                "label": label,
                "amount": self._round(values["amount"]),
                "invoice_count": values["invoice_count"],
            }
            for key, label in bucket_defs
            for values in [buckets[key]]
        ]

        row_response = []
        for vendor_id, values in vendor_rows.items():
            vendor = vendor_map.get(vendor_id, {})
            total = sum(values.values(), ZERO)
            row_response.append(
                {
                    "vendor_id": vendor_id,
                    "vendor_name": vendor.get("name") or "Unknown vendor",
                    "current": self._round(values["current"]),
                    "d1_30": self._round(values["1_30"]),
                    "d31_60": self._round(values["31_60"]),
                    "d61_90": self._round(values["61_90"]),
                    "d90_plus": self._round(values["90_plus"]),
                    "total": self._round(total),
                }
            )

        return {
            "buckets": bucket_response,
            "rows": sorted(row_response, key=lambda x: x["total"], reverse=True),
            "currency": currency,
        }
