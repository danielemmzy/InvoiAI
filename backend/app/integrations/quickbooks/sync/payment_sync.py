from __future__ import annotations

from app.core.enum.database import IntegrationProvider

from app.integrations.base.sync import BaseSyncService

from app.integrations.quickbooks.client import QuickBooksClient
from app.integrations.quickbooks.mapper import QuickBooksMapper

from app.services.document.document_sync_service import (
    DocumentSyncService,
)
from app.services.payment.payment_sync_service import (
    PaymentSyncService,
)
from app.services.vendor.vendor_sync_service import (
    VendorSyncService,
)


class QuickBooksPaymentSync(BaseSyncService):
    """
    Synchronize QuickBooks Payments.
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

        self.payment_service = PaymentSyncService()

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

        response = await self.client.payments()

        return (
            response.get("QueryResponse", {})
            .get("Payment", [])
        )

    async def map(
        self,
        payload: dict,
    ):

        vendor = None
        document = None

        customer_ref = payload.get(
            "CustomerRef",
        )

        if customer_ref:

            vendor = await self.vendor_service.get_by_external_id(
                org_id=self.org_id,
                provider=IntegrationProvider.QUICKBOOKS,
                external_id=str(
                    customer_ref["value"],
                ),
            )

        linked_transactions = []

        for line in payload.get(
            "Line",
            [],
        ):

            linked_transactions.extend(
                line.get(
                    "LinkedTxn",
                    [],
                )
            )

        for txn in linked_transactions:

            if txn.get(
                "TxnType",
            ) not in {
                "Invoice",
                "Bill",
            }:
                continue

            document = await self.document_service.get_external(
                org_id=self.org_id,
                provider=IntegrationProvider.QUICKBOOKS,
                external_id=str(
                    txn["TxnId"],
                ),
            )

            if document:
                break

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