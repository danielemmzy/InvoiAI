from __future__ import annotations

from app.integrations.base.sync import BaseSyncService

from app.integrations.quickbooks.client import QuickBooksClient
from app.integrations.quickbooks.mapper import QuickBooksMapper

from app.services.vendor.vendor_sync_service import VendorSyncService


class QuickBooksVendorSync(BaseSyncService):
    """
    Synchronize QuickBooks vendors.

    Responsibilities
    ----------------
    • Fetch vendors
    • Map vendors
    • Persist vendors

    No orchestration.
    """

    def __init__(
        self,
        *,
        org_id,
        realm_id: str,
    ) -> None:

        self.org_id = org_id

        self.vendor_service = VendorSyncService()

        super().__init__(
            client=QuickBooksClient(
                org_id=org_id,
                realm_id=realm_id,
            ),
            mapper=QuickBooksMapper(),
        )

    # =====================================================
    # BaseSync hooks
    # =====================================================

    async def fetch(
        self,
    ) -> list[dict]:

        response = await self.client.vendors()

        return (
            response.get("QueryResponse", {})
            .get("Vendor", [])
        )

    async def map(
        self,
        payload: dict,
    ):

        return self.mapper.vendor(
            org_id=self.org_id,
            data=payload,
        )

    async def persist(
        self,
        *,
        model,
        payload: dict,
    ) -> bool:

        existing = await self.vendor_service.repository.get_by_external_id(
            org_id=model.org_id,
            provider=model.provider,
            external_id=model.external_id,
        )

        await self.vendor_service.sync(
            model,
        )

        return existing is None