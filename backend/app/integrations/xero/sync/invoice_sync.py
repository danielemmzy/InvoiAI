from __future__ import annotations

from app.core.enum.database import IntegrationProvider

from app.integrations.base.sync import BaseSyncService

from app.integrations.xero.client import XeroClient
from app.integrations.xero.mapper import XeroMapper

from app.services.document.document_sync_service import (
    DocumentSyncService,
)
from app.services.vendor.vendor_sync_service import (
    VendorSyncService,
)


class XeroInvoiceSync(BaseSyncService):
    """
    Synchronize Xero Sales Invoices.
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.org_id = org_id

        self.vendor_service = VendorSyncService()

        self.document_service = DocumentSyncService()

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

        response = await self.client.invoices()

        invoices = response.get(
            "Invoices",
            [],
        )

        #
        # Only Accounts Receivable
        #

        return [
            invoice
            for invoice in invoices
            if invoice.get("Type") == "ACCREC"
        ]

    async def map(
        self,
        payload: dict,
    ):

        contact = payload.get(
            "Contact",
            {},
        )

        customer = await self.vendor_service.get_by_external_id(
            org_id=self.org_id,
            provider=IntegrationProvider.XERO,
            external_id=contact.get(
                "ContactID",
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

        existing = await self.document_service.get_by_external_id(
            org_id=model.org_id,
            provider=model.provider,
            external_id=model.external_id,
        )

        await self.document_service.sync(
            model,
        )

        return existing is None