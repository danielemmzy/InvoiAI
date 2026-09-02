from __future__ import annotations

from app.models.domain.payment import Payment
from app.repositories.document.payment_repository import (
    PaymentRepository,
)
from app.services.payment.payment_service import PaymentService
from app.models.domain.document import PurchaseOrder


class PaymentSyncService:
    """
    Shared payment synchronization service.

    Responsibilities
    ----------------
    • Persist external payments
    • Prevent duplicates
    • Delegate business logic to PaymentService

    Used by
    -------
    • QuickBooks
    • Xero
    • Sage

    No HTTP.

    No provider-specific logic.
    """

    def __init__(self):

        self.repository = PaymentRepository()

        self.payment_service = PaymentService()

    # =====================================================
    # Sync One
    # =====================================================

    async def sync(
        self,
        payment: Payment,
    ) -> Payment:

        existing = await self.repository.get_external(
            org_id=payment.org_id,
            provider=payment.provider,
            external_id=payment.external_id,
        )

        #
        # Existing payment
        #

        if existing:

            payment.id = existing.id

        #
        # Delegate persistence
        #

        return await self.payment_service.record_payment(
            payment,
        )

    # =====================================================
    # Sync Many
    # =====================================================

    async def sync_many(
        self,
        payments: list[Payment],
    ) -> list[Payment]:

        results: list[Payment] = []

        for payment in payments:

            results.append(
                await self.sync(
                    payment,
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