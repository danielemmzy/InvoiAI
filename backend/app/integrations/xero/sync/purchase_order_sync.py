from __future__ import annotations

from app.core.enum.database import IntegrationProvider

from app.integrations.base.sync import BaseSyncService

from app.integrations.xero.client import XeroClient
from app.integrations.xero.mapper import XeroMapper

from app.services.purchase.purchase_order_sync_service import (
    PurchaseOrderSyncService,
)
from app.services.vendor.vendor_sync_service import (
    VendorSyncService,
)


class XeroPurchaseOrderSync(BaseSyncService):
    """
    Synchronize Xero Purchase Orders.
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.org_id = org_id

        self.vendor_service = VendorSyncService()

        self.purchase_order_service = (
            PurchaseOrderSyncService()
        )

        super().__init__(
            client=XeroClient(
                org_id=org_id,
            ),
            mapper=XeroMapper(),
        )

    # =====================================================
    # BaseSync Hooks
    # =====================================================

    async def fetch(
        self,
    ) -> list[dict]:

        response = await self.client.purchase_orders()

        return response.get(
            "PurchaseOrders",
            [],
        )

    async def map(
        self,
        payload: dict,
    ):

        contact = payload.get(
            "Contact",
            {},
        )

        vendor = await self.vendor_service.get_by_external_id(
            org_id=self.org_id,
            provider=IntegrationProvider.XERO,
            external_id=contact.get(
                "ContactID",
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

        existing = (
            await self.purchase_order_service.get_by_external_id(
                org_id=model.org_id,
                provider=model.provider,
                external_id=model.external_id,
            )
        )

        await self.purchase_order_service.sync(
            model,
        )

        return existing is None