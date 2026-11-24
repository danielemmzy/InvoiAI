from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.db import execute
from app.core.supabase import get_supabase
from app.repositories.audit.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.document.workflow_router import route_for
from app.repositories.document.document_repository import DocumentRepository
from app.services.line_item_service import LineItemService


class DocumentNotFoundError(Exception):
    """The requested document does not exist in the current organization."""


class DocumentCaptureConflictError(Exception):
    """The document has advanced to a state where capture edits are blocked."""


class DocumentCaptureService:
    """Human-in-the-loop correction and master-data lookup for captured documents."""

    def __init__(self, repository: DocumentRepository | None = None, audit: AuditService | None = None, line_items: LineItemService | None = None):
        self.documents = repository or DocumentRepository()
        self.db = get_supabase()
        self.audit = audit or AuditService(repository=AuditRepository())
        self.line_items = line_items or LineItemService(repository=self.documents)

    async def update_capture(self, *, org_id: UUID, user_id: UUID, document_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        current_rows = (await execute(self.db.table("documents").select("*").eq("id", str(document_id)).eq("org_id", str(org_id)).limit(1))).data or []
        if not current_rows:
            raise DocumentNotFoundError("Document not found.")
        current = current_rows[0]
        if str(current.get("ap_status") or "") in {"approved", "syncing_to_erp", "payment_ready", "paid", "reconciled"}:
            raise DocumentCaptureConflictError("This document has advanced too far in AP to edit captured accounting data.")
        allowed = {
            "document_type", "vendor_id", "purchase_order_id", "vendor_name", "document_number", "document_date", "due_date",
            "currency", "payment_terms", "payment_method", "subtotal", "tax_rate", "tax_amount",
            "discount_amount", "total_amount", "amount_paid", "amount_due", "gl_account_id",
            "gl_account_code", "gl_account_name",
        }
        update = {k: v for k, v in payload.items() if k in allowed and v is not None}
        # GL account selection is persisted in capture_overrides. The base
        # documents table does not have denormalized GL code/name columns.
        gl_override = {k: update.pop(k) for k in ("gl_account_id", "gl_account_code", "gl_account_name") if k in update}
        if gl_override:
            current_overrides = current.get("capture_overrides") or {}
            if not isinstance(current_overrides, dict):
                current_overrides = {}
            update["capture_overrides"] = {**current_overrides, **gl_override}
        if "document_type" in update and hasattr(update["document_type"], "value"):
            update["document_type"] = update["document_type"].value
        if "document_type" in update:
            update["classification_confidence"] = 1.0
            update["classification_reason"] = "Human correction saved during document review."
            update["classified_at"] = datetime.now(UTC).isoformat()
            update["workflow_route"] = route_for(str(update["document_type"]))
        for key in ("vendor_id", "purchase_order_id"):
            if key in update and update[key] is not None:
                update[key] = str(update[key])
        for key in ("document_date", "due_date"):
            if key in update and hasattr(update[key], "isoformat"):
                update[key] = update[key].isoformat()
        for key in ("subtotal", "tax_rate", "tax_amount", "discount_amount", "total_amount", "amount_paid", "amount_due"):
            if key in update and update[key] is not None:
                update[key] = str(update[key])

        overrides = payload.get("overrides") or payload.get("capture_overrides")
        if isinstance(overrides, dict):
            current_overrides = current.get("capture_overrides") or {}
            if not isinstance(current_overrides, dict):
                current_overrides = {}
            update["capture_overrides"] = {**current_overrides, **overrides}
        has_mutation = bool(update) or payload.get("lines") is not None
        if has_mutation:
            ap_status = str(current.get("ap_status") or "received")
            ap_exception_active = bool(current.get("ap_enabled")) and ap_status in {"match_exception", "coding_exception", "on_hold"}
            update["updated_at"] = datetime.now(UTC).isoformat()
            update["error_message"] = None
            if ap_exception_active:
                # Corrections made while handling an AP exception must not silently
                # unenroll the invoice or erase its selected PO/receipt context.
                update["processing_step"] = current.get("processing_step") or "ap_exception_review"
                update["processing_message"] = "Invoice corrections saved. Resolve the AP exception to re-run the affected checks."
                update["processing_progress"] = current.get("processing_progress") or (55 if ap_status == "match_exception" else 85)
            else:
                update["intelligence_status"] = "not_requested"
                update["processing_step"] = "capture_complete"
                update["processing_message"] = "Document corrections saved; AI analysis can be run again."
                update["processing_progress"] = 100
                update["ap_status"] = "received"
                update["ap_enabled"] = False
            await execute(self.db.table("documents").update(update).eq("id", str(document_id)).eq("org_id", str(org_id)))

        if payload.get("lines") is not None:
            lines = []
            for item in payload["lines"] or []:
                metadata = {"human_edited": True}
                lines.append({**item, "metadata": metadata})
            await self.line_items.replace_items(org_id=org_id, document_id=document_id, items=lines)

        await self.audit.log_document_event(
            org_id=org_id, user_id=user_id, action="document.capture_edited", document_id=document_id,
            changed_fields=[k for k in payload.keys() if k != "lines"], line_count=len(payload.get("lines") or []) if payload.get("lines") is not None else None,
        )
        result = (await execute(self.db.table("documents").select("*").eq("id", str(document_id)).eq("org_id", str(org_id)).limit(1))).data or []
        return result[0] if result else current

    async def options(self, *, org_id: UUID, document_id: UUID, field: str, query: str = "") -> list[dict[str, Any]]:
        # The document row, its OCR capture and the field's suggestion list are
        # independent reads: all three are dispatched in the same round trip.
        q = (query or "").strip()
        suggestion_query = self._suggestion_query(org_id=org_id, field=field, query=q)

        async def _no_suggestions():
            return None

        doc_response, ocr_response, suggestions_response = await asyncio.gather(
            execute(
                self.db.table("documents").select("vendor_id,vendor_name,document_number,purchase_order_id,capture_overrides").eq("id", str(document_id)).eq("org_id", str(org_id)).limit(1)
            ),
            execute(
                self.db.table("ocr_results").select("key_value_pairs").eq("document_id", str(document_id)).eq("org_id", str(org_id)).order("created_at", desc=True).limit(1)
            ),
            execute(suggestion_query) if suggestion_query is not None else _no_suggestions(),
        )
        doc_rows = doc_response.data or []
        if not doc_rows:
            raise ValueError("Document not found.")
        doc = doc_rows[0]
        values: list[dict[str, Any]] = []
        ocr_rows = ocr_response.data or []
        kv = (ocr_rows[0].get("key_value_pairs") or {}) if ocr_rows else {}
        aliases = {
            "document_number": {"invoice_number", "invoice_no", "invoice_number_extracted", "po_number", "document_number"},
            "vendor_name": {"vendor_name", "supplier", "supplier_name"},
            "total_amount": {"total_amount", "total", "amount_due"},
            "currency": {"currency"},
            "document_date": {"document_date", "invoice_date", "date"},
            "due_date": {"due_date"},
        }
        keys = aliases.get(field, {field})
        for key, value in kv.items():
            if key in keys and value not in (None, "", []):
                values.append({"value": str(value), "label": str(value), "source": "captured"})
        overrides = doc.get("capture_overrides") or {}
        if not isinstance(overrides, dict):
            overrides = {}
        current_value = overrides.get(field) if field.startswith("gl_account") else doc.get(field)
        if current_value not in (None, ""):
            values.append({"value": str(current_value), "label": str(current_value), "source": "current"})
        for row in (suggestions_response.data if suggestions_response is not None else []) or []:
            if field == "vendor_name":
                values.append({"value": row["name"], "label": row["name"], "source": "vendor", "id": row["id"]})
            elif field in {"gl_account_name", "gl_account_id"}:
                values.append({"value": row["account_name"], "label": f"{row.get('account_code') or ''} · {row['account_name']}", "source": "chart_of_accounts", "id": row["id"], "code": row.get("account_code")})
            elif field == "document_number":
                values.append({"value": row["po_number"], "label": row["po_number"], "source": "purchase_order", "id": row["id"]})
        dedup: dict[str, dict[str, Any]] = {}
        for item in values:
            key = str(item.get("value") or "").strip().lower()
            if key and key not in dedup:
                dedup[key] = item
        return list(dedup.values())[:50]

    def _suggestion_query(self, *, org_id: UUID, field: str, query: str):
        """Build the field's suggestion query, or None when it has no lookup."""
        if field == "vendor_name":
            query_builder = self.db.table("vendors").select("id,name").eq("org_id", str(org_id)).limit(25)
            return query_builder.ilike("name", f"%{query}%") if query else query_builder
        if field in {"gl_account_name", "gl_account_id"}:
            query_builder = self.db.table("chart_of_accounts").select("id,account_code,account_name,account_type").eq("org_id", str(org_id)).eq("is_active", True).limit(50)
            return query_builder.or_(f"account_name.ilike.%{query}%,account_code.ilike.%{query}%") if query else query_builder
        if field == "document_number":
            query_builder = self.db.table("purchase_orders").select("id,po_number").eq("org_id", str(org_id)).limit(25)
            return query_builder.ilike("po_number", f"%{query}%") if query else query_builder
        return None
