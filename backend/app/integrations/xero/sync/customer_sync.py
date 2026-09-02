from __future__ import annotations

from app.integrations.base.sync import BaseSyncService

from app.integrations.xero.client import XeroClient
from app.integrations.xero.mapper import XeroMapper

from app.services.vendor.vendor_sync_service import (
    VendorSyncService,
)


class XeroCustomerSync(BaseSyncService):
    """
    Synchronize Xero Contacts (Customers).
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.org_id = org_id

        self.vendor_service = VendorSyncService()

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

        response = await self.client.contacts()

        return response.get(
            "Contacts",
            [],
        )

    async def map(
        self,
        payload: dict,
    ):

        return self.mapper.customer(
            org_id=self.org_id,
            data=payload,
        )

    async def persist(
        self,
        *,
        model,
        payload: dict,
    ) -> bool:

        existing = await self.vendor_service.get_by_external_id(
            org_id=model.org_id,
            provider=model.provider,
            external_id=model.external_id,
        )

        await self.vendor_service.sync(
            model,
        )

        return existing is None