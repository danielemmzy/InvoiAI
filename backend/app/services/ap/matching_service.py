from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.core.enum.ap import APExceptionType, APMatchStatus
from app.core.supabase import get_supabase
from app.repositories.ap.exception_repository import InvoiceExceptionRepository
from app.repositories.ap.goods_receipt_repository import GoodsReceiptRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MatchResult:
    status: APMatchStatus
    passed: bool
    exceptions: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class MatchingService:
    """Deterministic 2-way/3-way AP matching.

    Matching is line-aware where PO/receipt line data is available and falls
    back to document-level checks only when the source system has no line data.
    Tolerances are tenant-configurable and are never decided by an LLM.
    """

    DEFAULT_QTY_TOL = Decimal("5")
    DEFAULT_PRICE_TOL = Decimal("2")
    DEFAULT_AMOUNT_TOL = Decimal("50")

    def __init__(self, db=None):
        self.db = db or get_supabase()
        self.exceptions = InvoiceExceptionRepository()
        self.receipts = GoodsReceiptRepository()

    async def run(
        self,
        *,
        org_id: UUID,
        document_id: UUID,
        document: dict,
        line_items: list[dict],
        purchase_order: dict | None,
    ) -> MatchResult:
        if not purchase_order:
            self._update_document(
                org_id, document_id,
                match_status=APMatchStatus.NOT_REQUIRED.value,
                two_way_match_passed=True,
                three_way_match_passed=None,
                match_exception_count=0,
            )
            return MatchResult(APMatchStatus.NOT_REQUIRED, True)

        tol = self._get_tolerance(org_id, document, purchase_order)
        exceptions: list[dict] = []

        # Header controls.
        inv_vendor = document.get("vendor_id")
        po_vendor = purchase_order.get("vendor_id")
        if inv_vendor and po_vendor and str(inv_vendor) != str(po_vendor):
            exceptions.append(self._exc(
                APExceptionType.PRICE_MISMATCH,
                "Vendor mismatch: invoice vendor does not match PO",
                str(po_vendor), str(inv_vendor), "critical",
            ))

        inv_currency = (document.get("currency") or "").upper()
        po_currency = (purchase_order.get("currency") or "").upper()
        if inv_currency and po_currency and inv_currency != po_currency:
            exceptions.append(self._exc(
                APExceptionType.CURRENCY_MISMATCH, "Currency mismatch",
                po_currency, inv_currency, "critical",
            ))

        po_amount = self._decimal(
            purchase_order.get("amount")
            or purchase_order.get("total_amount")
            or purchase_order.get("total")
        )
        inv_amount = self._decimal(document.get("total_amount"))
        amount_variance = abs(inv_amount - po_amount)
        amount_pct = (amount_variance / po_amount * 100) if po_amount else Decimal("0")

        if po_amount and (
            amount_variance > tol["amount_absolute"]
            and amount_pct > tol["price_percent"]
        ):
            kind = (
                APExceptionType.AMOUNT_EXCEEDS_PO
                if inv_amount > po_amount
                else APExceptionType.PRICE_MISMATCH
            )
            exceptions.append(self._exc(
                kind,
                f"Invoice amount variance {amount_pct:.2f}% exceeds tolerance",
                str(po_amount), str(inv_amount), "warning", f"{amount_pct:.2f}%",
            ))

        # 2-way line matching: quantity and unit price against PO lines.
        po_lines = self._extract_po_lines(purchase_order)
        line_meta = {"po_line_count": len(po_lines)}
        if po_lines and line_items:
            line_exceptions = self._match_lines(line_items, po_lines, tol)
            exceptions.extend(line_exceptions)
        elif not po_lines:
            line_meta["line_match"] = "header_only"

        # 3-way matching: invoice quantities must not exceed confirmed receipts
        # beyond tolerance. Receipt repository is tenant scoped.
        receipts = await self.receipts.get_confirmed_for_po(
            org_id, UUID(str(purchase_order["id"]))
        )
        three_way: bool | None = None
        requires_three_way = tol["match_mode"] == "three_way"
        if receipts:
            receipt_lines = self._receipt_quantities(receipts)
            if receipt_lines and line_items:
                qty_exceptions = self._match_receipts(line_items, receipt_lines, tol)
                exceptions.extend(qty_exceptions)
                three_way = not any(
                    e["exception_type"] == APExceptionType.QUANTITY_MISMATCH.value
                    for e in qty_exceptions
                )
            else:
                received = sum(
                    (self._decimal(line.quantity_received) for r in receipts for line in r.lines),
                    Decimal("0"),
                )
                invoiced = sum(
                    (self._decimal(x.get("quantity")) for x in line_items),
                    Decimal("0"),
                )
                if invoiced and abs(invoiced - received) / invoiced * 100 > tol["quantity_percent"]:
                    exceptions.append(self._exc(
                        APExceptionType.QUANTITY_MISMATCH,
                        "Invoice quantity differs from received quantity",
                        str(received), str(invoiced), "warning",
                        f"{abs(invoiced-received)/invoiced*100:.2f}%",
                    ))
                three_way = not any(
                    e["exception_type"] == APExceptionType.QUANTITY_MISMATCH.value
                    for e in exceptions
                )
        else:
            three_way = False if requires_three_way else None
            line_meta["three_way"] = "required_but_missing" if requires_three_way else "not_required"
            if requires_three_way:
                exceptions.append(self._exc(
                    APExceptionType.MISSING_RECEIPT,
                    "Three-way match requires a confirmed goods receipt",
                    "confirmed receipt", "none", "warning",
                ))

        for data in exceptions:
            await self.exceptions.create_exception(
                __import__("app.models.domain.ap", fromlist=["InvoiceException"])
                .InvoiceException(org_id=org_id, document_id=document_id, **data)
            )

        two_way_failed = any(
            e["exception_type"] in {
                APExceptionType.PRICE_MISMATCH.value,
                APExceptionType.CURRENCY_MISMATCH.value,
                APExceptionType.AMOUNT_EXCEEDS_PO.value,
            }
            or e["exception_type"] == APExceptionType.QUANTITY_MISMATCH.value
            for e in exceptions
        )
        status = APMatchStatus.EXCEPTION if exceptions else APMatchStatus.MATCHED
        self._update_document(
            org_id, document_id,
            match_status=status.value,
            two_way_match_passed=not two_way_failed,
            three_way_match_passed=three_way,
            match_exception_count=len(exceptions),
        )
        return MatchResult(status, not exceptions, exceptions, line_meta)

    def _get_tolerance(self, org_id: UUID, document: dict, po: dict) -> dict:
        # Most specific scope wins: vendor -> document type -> org.
        q = self.db.table("matching_tolerances").select("*").eq("org_id", str(org_id))
        rows = q.execute().data or []
        vendor = str(document.get("vendor_id") or po.get("vendor_id") or "")
        dtype = str(document.get("document_type") or "invoice")
        candidates = []
        for row in rows:
            scope = row.get("scope")
            if scope == "vendor" and str(row.get("vendor_id")) == vendor:
                candidates.append((3, row))
            elif scope == "document_type" and row.get("document_type") == dtype:
                candidates.append((2, row))
            elif scope == "org":
                candidates.append((1, row))
        if not candidates:
            return {"quantity_percent": self.DEFAULT_QTY_TOL, "price_percent": self.DEFAULT_PRICE_TOL, "amount_absolute": self.DEFAULT_AMOUNT_TOL, "match_mode": "auto"}
        row = max(candidates, key=lambda x: x[0])[1]
        return {
            "quantity_percent": self._decimal(row.get("quantity_percent"), self.DEFAULT_QTY_TOL),
            "price_percent": self._decimal(row.get("price_percent"), self.DEFAULT_PRICE_TOL),
            "amount_absolute": self._decimal(row.get("amount_absolute"), self.DEFAULT_AMOUNT_TOL),
            "match_mode": row.get("match_mode") or "auto",
        }

    @staticmethod
    def _extract_po_lines(po: dict) -> list[dict]:
        for key in ("line_items", "lines", "purchase_order_lines", "Line", "line"):
            value = po.get(key)
            if isinstance(value, list):
                return value
        return []

    def _match_lines(self, invoice_lines, po_lines, tol):
        exceptions = []
        used = set()
        for inv in invoice_lines:
            candidates = []
            inv_sku = str(inv.get("sku") or "").strip().lower()
            inv_desc = str(inv.get("description") or "").strip().lower()
            for i, po in enumerate(po_lines):
                if i in used:
                    continue
                sku = str(po.get("sku") or po.get("item_code") or "").strip().lower()
                desc = str(po.get("description") or po.get("item_name") or "").strip().lower()
                if inv_sku and sku and inv_sku == sku:
                    candidates.append((2, i, po))
                elif inv_desc and desc and (inv_desc in desc or desc in inv_desc):
                    candidates.append((1, i, po))
            if not candidates:
                exceptions.append(self._exc(
                    APExceptionType.PRICE_MISMATCH,
                    "Invoice line could not be matched to a PO line",
                    "matching PO line", inv.get("description") or inv.get("sku") or "unknown", "warning",
                ))
                continue
            _, idx, po = max(candidates, key=lambda x: x[0])
            used.add(idx)
            inv_qty = self._decimal(inv.get("quantity"))
            po_qty = self._decimal(po.get("quantity") or po.get("qty"))
            if po_qty and inv_qty > po_qty * (1 + tol["quantity_percent"] / 100):
                exceptions.append(self._exc(
                    APExceptionType.QUANTITY_MISMATCH,
                    "Invoice quantity exceeds PO quantity beyond tolerance",
                    str(po_qty), str(inv_qty), "warning",
                    f"{(inv_qty-po_qty)/po_qty*100:.2f}%",
                ))
            inv_price = self._decimal(inv.get("unit_price") or inv.get("unitPrice"))
            po_price = self._decimal(po.get("unit_price") or po.get("unitPrice") or po.get("price"))
            if po_price:
                pct = abs(inv_price - po_price) / po_price * 100
                if pct > tol["price_percent"]:
                    exceptions.append(self._exc(
                        APExceptionType.PRICE_MISMATCH,
                        "Invoice unit price exceeds PO tolerance",
                        str(po_price), str(inv_price), "warning", f"{pct:.2f}%",
                    ))
            po_line_amount = self._decimal(po.get("amount") or po.get("line_amount") or po.get("total"))
            inv_line_amount = self._decimal(inv.get("amount") or inv.get("line_total"))
            if po_line_amount and inv_line_amount:
                pct = abs(inv_line_amount - po_line_amount) / po_line_amount * 100
                if pct > tol["price_percent"] and abs(inv_line_amount - po_line_amount) > tol["amount_absolute"]:
                    exceptions.append(self._exc(
                        APExceptionType.PRICE_MISMATCH,
                        "Invoice line amount exceeds PO tolerance",
                        str(po_line_amount), str(inv_line_amount), "warning", f"{pct:.2f}%",
                    ))
        return exceptions

    def _match_receipts(self, invoice_lines, receipt_lines, tol):
        exceptions = []
        for inv in invoice_lines:
            key = self._line_key(inv)
            received = receipt_lines.get(key, Decimal("0"))
            invoiced = self._decimal(inv.get("quantity"))
            if invoiced and invoiced > received * (1 + tol["quantity_percent"] / 100):
                pct = (invoiced - received) / invoiced * 100
                exceptions.append(self._exc(
                    APExceptionType.QUANTITY_MISMATCH,
                    "Invoice quantity exceeds confirmed receipt quantity beyond tolerance",
                    str(received), str(invoiced), "warning", f"{pct:.2f}%",
                ))
        return exceptions

    @staticmethod
    def _receipt_quantities(receipts):
        out = {}
        for receipt in receipts:
            for line in receipt.lines:
                key = str(getattr(line, "sku", None) or getattr(line, "description", None) or "").strip().lower()
                if key:
                    out[key] = out.get(key, Decimal("0")) + Decimal(str(line.quantity_received))
        return out

    @staticmethod
    def _line_key(line):
        return str(line.get("sku") or line.get("description") or "").strip().lower()

    @staticmethod
    def _decimal(value, default=Decimal("0")):
        try:
            return Decimal(str(value)) if value not in (None, "") else default
        except (InvalidOperation, ValueError, TypeError):
            return default

    def _update_document(self, org_id, document_id, **values):
        self.db.table("documents").update(values).eq(
            "id", str(document_id)
        ).eq("org_id", str(org_id)).execute()

    @staticmethod
    def _exc(kind, title, expected, actual, severity, variance=None):
        return {
            "exception_type": kind.value,
            "status": "open",
            "severity": severity,
            "title": title,
            "expected_value": expected,
            "actual_value": actual,
            "variance": variance,
        }
