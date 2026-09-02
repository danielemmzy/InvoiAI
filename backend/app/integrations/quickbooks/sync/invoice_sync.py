from __future__ import annotations

from app.core.enum.database import IntegrationProvider

from app.integrations.base.sync import BaseSyncService

from app.integrations.quickbooks.client import QuickBooksClient
from app.integrations.quickbooks.mapper import QuickBooksMapper

from app.services.document.document_sync_service import (
    DocumentSyncService,
)
from app.services.vendor.vendor_sync_service import (
    VendorSyncService,
)


class QuickBooksInvoiceSync(BaseSyncService):
    """
    Synchronize QuickBooks Invoices.
    """

    def __init__(
        self,
        *,
        org_id,
        realm_id: str,
    ) -> None:

        self.org_id = org_id

        self.vendor_service = VendorSyncService()

        self.document_service = DocumentSyncService()

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

        response = await self.client.invoices()

        return (
            response.get("QueryResponse", {})
            .get("Invoice", [])
        )

    async def map(
        self,
        payload: dict,
    ):

        customer = await self.vendor_service.get_by_external_id(
            org_id=self.org_id,
            provider=IntegrationProvider.QUICKBOOKS,
            external_id=str(
                payload["CustomerRef"]["value"],
            ),
        )

        if customer is None:
            return None

        return self.mapper.invoice(
            org_id=self.org_id,
            vendor_id=customer.id,
            data=payload,
        )

    async def persist(
        self,
        *,
        model,
        payload: dict,
    ) -> bool:

        existing = await self.document_service.get_external(
            org_id=model.org_id,
            provider=model.provider, 
            external_id=model.external_id,
        )

        await self.document_service.sync(
            model,
        )

        return existing is None