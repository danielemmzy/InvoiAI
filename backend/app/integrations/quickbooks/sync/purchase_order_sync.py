from __future__ import annotations

from app.core.enum.database import IntegrationProvider

from app.integrations.base.sync import BaseSyncService

from app.integrations.quickbooks.client import QuickBooksClient
from app.integrations.quickbooks.mapper import QuickBooksMapper

from app.services.purchase.purchase_order_sync_service import (
    PurchaseOrderSyncService,
)
from app.services.vendor.vendor_sync_service import (
    VendorSyncService,
)


class QuickBooksPurchaseOrderSync(BaseSyncService):
    """
    Synchronize QuickBooks Purchase Orders.
    """

    def __init__(
        self,
        *,
        org_id,
        realm_id: str,
    ) -> None:

        self.org_id = org_id

        self.vendor_service = VendorSyncService()

        self.purchase_order_service = (
            PurchaseOrderSyncService()
        )

        super().__init__(
            client=QuickBooksClient(
                org_id=org_id,
                realm_id=realm_id,
            ),
            mapper=QuickBooksMapper(),
        )

    # =====================================================
    # BaseSync Hooks
    # =====================================================

    async def fetch(
        self,
    ) -> list[dict]:

        response = await self.client.purchase_orders()

        return (
            response.get("QueryResponse", {})
            .get("PurchaseOrder", [])
        )

    async def map(
        self,
        payload: dict,
    ):

        vendor = await self.vendor_service.get_by_external_id(
            org_id=self.org_id,
            provider=IntegrationProvider.QUICKBOOKS,
            external_id=str(
                payload["VendorRef"]["value"],
            ),
        )

        if vendor is None:
            return None

        return self.mapper.purchase_order(
            org_id=self.org_id,
            vendor_id=vendor.id,
            data=payload,
        )

    async def persist(
        self,
        *,
        model,
        payload: dict,
    ) -> bool:

        existing = await self.purchase_order_service.get_by_external_id(
            org_id=model.org_id,
            provider=model.provider,
            external_id=model.external_id,
        )

        await self.purchase_order_service.sync(
            model,
        )

        return existing is None