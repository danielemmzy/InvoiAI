from __future__ import annotations

from app.models.domain.purchase_order import PurchaseOrder
from app.repositories.document.purchase_order_repository import (
    PurchaseOrderRepository,
)


class PurchaseOrderSyncService:
    """
    Shared Purchase Order synchronization service.

    Responsibilities
    ----------------
    • Synchronize Purchase Orders from ERP providers
    • Prevent duplicates
    • Update existing records
    • Delegate persistence to the repository

    Used by
    -------
    • QuickBooks
    • Xero
    • Sage

    No provider-specific logic.

    No HTTP.
    """

    def __init__(self):

        self.repository = PurchaseOrderRepository()

    # =====================================================
    # Sync One
    # =====================================================

    async def sync(
        self,
        purchase_order: PurchaseOrder,
    ) -> PurchaseOrder:

        existing = None

        #
        # Match provider + external_id
        #

        if (
            purchase_order.external_id
            and purchase_order.provider
        ):

            existing = (
                await self.repository.get_by_external_id(
                    org_id=purchase_order.org_id,
                    provider=purchase_order.provider,
                    external_id=purchase_order.external_id,
                )
            )

        #
        # Fallback to PO Number
        #

        if (
            existing is None
            and purchase_order.po_number
        ):

            existing = (
                await self.repository.get_by_number(
                    org_id=purchase_order.org_id,
                    po_number=purchase_order.po_number,
                )
            )

        if existing:

            purchase_order.id = existing.id

        return await self.repository.upsert_external(
            purchase_order,
        )

    # =====================================================
    # Sync Many
    # =====================================================

    async def sync_many(
        self,
        purchase_orders: list[PurchaseOrder],
    ) -> list[PurchaseOrder]:

        results: list[PurchaseOrder] = []

        for purchase_order in purchase_orders:

            results.append(
                await self.sync(
                    purchase_order,
                )
            )

        return results

    # =====================================================
    # Lookup
    # =====================================================

    async def get_by_external_id(
        self,
        *,
        org_id,
        provider,
        external_id: str,
    ) -> PurchaseOrder | None:

        return await self.repository.get_by_external_id(
            org_id=org_id,
            provider=provider,
            external_id=external_id,
        )