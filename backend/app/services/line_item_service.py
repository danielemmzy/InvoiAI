"""
============================================================
Line Item Service

Business logic for extracted document line items.

Responsibilities
----------------
- Create extracted line items
- Retrieve line items
- Update line items
- Delete line items
- Calculate totals

Repository handles persistence.

No OCR.
No AI.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from app.repositories.document.document_repository import DocumentRepository


class LineItemService:
    """Keep line-item edits tenant-scoped, decimal-safe, and traceable."""

    _EDITABLE_FIELDS = {
        "description", "quantity", "unit_price", "amount", "tax_rate", "tax_amount", "discount",
        "sku", "product_code", "unit_type", "category", "sub_category", "gl_account", "cost_center", "project_code",
    }
    _DECIMAL_FIELDS = {"quantity", "unit_price", "amount", "tax_rate", "tax_amount", "discount"}

    def __init__(self, repository: DocumentRepository | None = None) -> None:
        self.repository = repository or DocumentRepository()

    async def create_items(self, *, org_id: UUID, document_id: UUID, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if await self.repository.get_document_for_org(org_id=org_id, document_id=document_id) is None:
            raise ValueError("Document not found.")
        normalized = [self._normalize_item(item, position=index) for index, item in enumerate(items, start=1)]
        return await self.repository.create_document_line_items(org_id=org_id, document_id=document_id, items=normalized)

    async def replace_items(self, *, org_id: UUID, document_id: UUID, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if await self.repository.get_document_for_org(org_id=org_id, document_id=document_id) is None:
            raise ValueError("Document not found.")
        normalized = [self._normalize_item(item, position=index) for index, item in enumerate(items, start=1)]
        return await self.repository.replace_document_line_items(document_id=document_id, org_id=org_id, items=normalized)

    async def get_items(self, *, org_id: UUID, document_id: UUID) -> list[dict[str, Any]]:
        return await self.repository.list_document_line_items(org_id=org_id, document_id=document_id)

    async def update_item(self, *, org_id: UUID, item_id: UUID, changes: dict[str, Any], actor_id: UUID | None = None) -> dict[str, Any]:
        current = await self.repository.get_document_line_item(org_id=org_id, item_id=item_id)
        if current is None:
            raise ValueError("Line item not found.")
        update = {key: value for key, value in changes.items() if key in self._EDITABLE_FIELDS and value is not None}
        if not update:
            raise ValueError("At least one editable line-item value is required.")
        normalized = self._normalize_item({**current, **update}, position=int(current.get("position") or 1))
        update = {key: normalized[key] for key in update}
        metadata = dict(current.get("metadata") or {})
        corrections = list(metadata.get("corrections") or [])
        corrections.append({"actor_id": str(actor_id) if actor_id else None, "changed_at": datetime.now(UTC).isoformat(), "before": {key: self._as_storage_value(current.get(key)) for key in update}, "after": {key: update[key] for key in update}})
        metadata["corrections"] = corrections
        update["metadata"] = metadata
        return await self.repository.update_document_line_item(org_id=org_id, item_id=item_id, data=update)

    async def delete_item(self, *, org_id: UUID, item_id: UUID) -> None:
        if await self.repository.get_document_line_item(org_id=org_id, item_id=item_id) is None:
            raise ValueError("Line item not found.")
        await self.repository.delete_document_line_item(org_id=org_id, item_id=item_id)

    async def calculate_totals(self, *, org_id: UUID, document_id: UUID) -> dict[str, Decimal]:
        items = await self.get_items(org_id=org_id, document_id=document_id)
        subtotal = sum((self._decimal(item.get("amount"), "amount") for item in items), Decimal("0"))
        tax = sum((self._decimal(item.get("tax_amount"), "tax_amount", nullable=True) for item in items), Decimal("0"))
        discount = sum((self._decimal(item.get("discount"), "discount", nullable=True) for item in items), Decimal("0"))
        return {"line_subtotal": subtotal, "tax_amount": tax, "discount_amount": discount, "total_amount": subtotal + tax - discount}

    def _normalize_item(self, item: dict[str, Any], *, position: int) -> dict[str, Any]:
        result: dict[str, Any] = {"position": position, "description": str(item.get("description") or "")}
        for field in self._DECIMAL_FIELDS:
            value = self._decimal(item.get(field), field, nullable=field in {"tax_rate", "tax_amount", "discount"})
            if value is not None and value < 0:
                raise ValueError(f"{field} cannot be negative.")
            result[field] = self._as_storage_value(value) if value is not None else None
        for field in self._EDITABLE_FIELDS - self._DECIMAL_FIELDS - {"description"}:
            if field in item:
                result[field] = item[field]
        metadata = dict(item.get("metadata") or {})
        if item.get("gl_account_id"):
            metadata["gl_account_id"] = str(item["gl_account_id"])
        if item.get("gl_account_code"):
            metadata["gl_account_code"] = item["gl_account_code"]
        if item.get("gl_account_name"):
            metadata["gl_account_name"] = item["gl_account_name"]
        if item.get("gl_account_code") or item.get("gl_account_name"):
            result["gl_account"] = item.get("gl_account_code") or item.get("gl_account_name")
        result["metadata"] = metadata
        return result

    @staticmethod
    def _decimal(value: Any, field: str, *, nullable: bool = False) -> Decimal | None:
        if value in (None, "") and nullable:
            return None
        try:
            result = Decimal(str(0 if value in (None, "") else value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"{field} must be a valid decimal amount.") from exc
        if not result.is_finite():
            raise ValueError(f"{field} must be a finite decimal amount.")
        return result

    @staticmethod
    def _as_storage_value(value: Any) -> Any:
        return str(value) if isinstance(value, Decimal) else value
