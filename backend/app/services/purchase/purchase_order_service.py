from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.models.domain.purchase_order import PurchaseOrder
from app.repositories.document.purchase_order_repository import (
    PurchaseOrderRepository,
)


class PurchaseOrderService:
    """
    Core Purchase Order business service.

    Responsibilities
    ----------------
    • Purchase Order CRUD
    • Matching business rules
    • Matched amount calculations
    • Purchase Order lifecycle

    ERP synchronization is handled by
    PurchaseOrderSyncService.
    """

    def __init__(self):

        self.repository = PurchaseOrderRepository()

    # =====================================================
    # CRUD
    # =====================================================

    async def create(
        self,
        purchase_order: PurchaseOrder,
    ) -> PurchaseOrder:

        return await self.repository.create_purchase_order(
            purchase_order,
        )

    async def get(
        self,
        purchase_order_id: UUID,
    ) -> PurchaseOrder | None:

        return await self.repository.get_purchase_order(
            purchase_order_id,
        )

    async def list_purchase_orders(
        self,
        *,
        org_id: UUID,
        vendor_id: UUID | None = None,
        is_open: bool | None = None,
        search: str | None = None,
        date_from=None,
        date_to=None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        rows, total = await self.repository.list_purchase_orders(
            org_id,
            vendor_id=vendor_id,
            is_open=is_open,
            search=search,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

        def _status(row: dict) -> str:
            amount = Decimal(str(row.get("amount") or 0))
            matched = Decimal(str(row.get("matched_amount") or 0))
            if matched <= 0:
                return "open"
            if matched >= amount:
                return "matched"
            return "partially_matched"

        items = [
            {
                "id": row["id"],
                "po_number": row.get("po_number"),
                "vendor_id": row.get("vendor_id"),
                "vendor_name": (row.get("vendors") or {}).get("name") if isinstance(row.get("vendors"), dict) else None,
                "amount": row.get("amount"),
                "matched_amount": row.get("matched_amount") or 0,
                "currency": row.get("currency", "USD"),
                "is_open": row.get("is_open", True),
                "issued_date": row.get("issued_date"),
                "expiry_date": row.get("expiry_date"),
                "status": _status(row),
            }
            for row in rows
        ]

        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def update(
        self,
        purchase_order_id: UUID,
        values: dict,
    ) -> PurchaseOrder | None:

        return await self.repository.update_purchase_order(
            purchase_order_id,
            values,
        )

    async def delete(
        self,
        purchase_order_id: UUID,
    ) -> bool:

        return await self.repository.delete_purchase_order(
            purchase_order_id,
        )

    # =====================================================
    # Queries
    # =====================================================

    async def get_by_number(
        self,
        *,
        org_id: UUID,
        po_number: str,
    ) -> PurchaseOrder | None:

        return await self.repository.get_by_number(
            org_id=org_id,
            po_number=po_number,
        )

    async def get_by_external_id(
        self,
        *,
        org_id: UUID,
        provider,
        external_id: str,
    ) -> PurchaseOrder | None:

        return await self.repository.get_by_external_id(
            org_id=org_id,
            provider=provider,
            external_id=external_id,
        )

    async def list_open(
        self,
        *,
        org_id: UUID,
    ) -> list[PurchaseOrder]:

        return await self.repository.list_open(
            org_id=org_id,
        )

    async def list_vendor_purchase_orders(
        self,
        *,
        org_id: UUID,
        vendor_id: UUID,
    ) -> list[PurchaseOrder]:

        return await self.repository.list_vendor_purchase_orders(
            org_id=org_id,
            vendor_id=vendor_id,
        )

    # =====================================================
    # Matching
    # =====================================================

    async def match_document(
        self,
        *,
        org_id: UUID,
        po_number: str,
    ) -> PurchaseOrder | None:
        """
        Locate the Purchase Order matching
        a document.
        """

        return await self.repository.match_document(
            org_id=org_id,
            po_number=po_number,
        )

    async def recalculate_matched_amount(
        self,
        purchase_order: PurchaseOrder,
        matched_amount: Decimal,
    ) -> PurchaseOrder | None:
        """
        Update matched amount and automatically
        determine whether the PO remains open.
        """

        purchase_order.matched_amount = matched_amount

        purchase_order.is_open = (
            matched_amount < purchase_order.amount
        )

        return await self.repository.update_purchase_order(
            purchase_order.id,
            purchase_order,
        )

    async def close_if_fully_matched(
        self,
        purchase_order: PurchaseOrder,
    ) -> PurchaseOrder | None:
        """
        Close the Purchase Order once the
        full amount has been matched.
        """

        if purchase_order.matched_amount >= purchase_order.amount:

            purchase_order.is_open = False

            return await self.repository.update_purchase_order(
                purchase_order.id,
                purchase_order,
            )

        return purchase_order

    async def reopen_if_needed(
        self,
        purchase_order: PurchaseOrder,
    ) -> PurchaseOrder | None:
        """
        Reopen the Purchase Order when
        allocations are removed.
        """

        if purchase_order.matched_amount < purchase_order.amount:

            purchase_order.is_open = True

            return await self.repository.update_purchase_order(
                purchase_order.id,
                purchase_order,
            )

        return purchase_order