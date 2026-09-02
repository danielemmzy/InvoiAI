from __future__ import annotations

from app.core.enum.database import IntegrationProvider

from app.integrations.base.sync import BaseSyncService

from app.integrations.xero.client import XeroClient
from app.integrations.xero.mapper import XeroMapper

from app.services.document.document_sync_service import (
    DocumentSyncService,
)
from app.services.payment.payment_sync_service import (
    PaymentSyncService,
)
from app.services.vendor.vendor_sync_service import (
    VendorSyncService,
)


class XeroPaymentSync(BaseSyncService):
    """
    Synchronize Xero Payments.
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.org_id = org_id

        self.vendor_service = VendorSyncService()

        self.document_service = DocumentSyncService()

        self.payment_service = PaymentSyncService()

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

        response = await self.client.payments()

        return response.get(
            "Payments",
            [],
        )

    async def map(
        self,
        payload: dict,
    ):

        vendor = None
        document = None

        contact = payload.get(
            "Invoice",
            {},
        ).get(
            "Contact",
            {},
        )

        if contact:

            vendor = await self.vendor_service.get_by_external_id(
                org_id=self.org_id,
                provider=IntegrationProvider.XERO,
                external_id=contact.get(
                    "ContactID",
                ),
            )

        invoice = payload.get(
            "Invoice",
            {},
        )

        if invoice:

            document = await self.document_service.get_by_external_id(
                org_id=self.org_id,
                provider=IntegrationProvider.XERO,
                external_id=invoice.get(
                    "InvoiceID",
                ),
            )

        return self.mapper.payment(
            org_id=self.org_id,
            vendor_id=vendor.id if vendor else None,
            document_id=document.id if document else None,
            data=payload,
        )

    async def persist(
        self,
        *,
        model,
        payload: dict,
    ) -> bool:

        existing = await self.payment_service.get_by_external_id(
            org_id=model.org_id,
            provider=model.provider,
            external_id=model.external_id,
        )

        await self.payment_service.sync(
            model,
        )

        return existing is None