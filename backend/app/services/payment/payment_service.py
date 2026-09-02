from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from app.models.domain.payment import Payment
from app.models.domain.payment_allocation import PaymentAllocation
from app.repositories.document.document_repository import DocumentRepository
from app.repositories.document.payment_allocation import (
    PaymentAllocationRepository,
)
from app.repositories.document.payment_repository import (
    PaymentRepository,
)


class PaymentService:
    """
    ERP Payment Service.

    Responsibilities
    ----------------
    • Record external payments
    • Allocate payments
    • Maintain document balances
    • Update payment status

    No provider-specific logic.
    """

    def __init__(self):

        self.payment_repository = PaymentRepository()

        self.document_repository = DocumentRepository()

        self.allocation_repository = (
            PaymentAllocationRepository()
        )

    # =====================================================
    # Payment
    # =====================================================

    async def record_payment(
        self,
        payment: Payment,
    ) -> Payment:

        return await self.payment_repository.upsert_external(
            payment,
        )

    # =====================================================
    # Allocation
    # =====================================================

    async def allocate_payment(
        self,
        *,
        payment: Payment,
        document_id: UUID,
        amount: Decimal,
    ):

        allocation = PaymentAllocation(
            id=uuid4(),
            org_id=payment.org_id,
            payment_id=payment.id,
            document_id=document_id,
            allocated_amount=amount,
        )

        allocation = (
            await self.allocation_repository.create_allocation(
                allocation,
            )
        )

        await self.recalculate_document(
            document_id,
        )

        return allocation

    # =====================================================
    # Document Balance
    # =====================================================

    async def recalculate_document(
        self,
        document_id: UUID,
    ):

        document = (
            await self.document_repository.get_document(
                document_id,
            )
        )

        if document is None:
            return None

        allocations = (
            await self.allocation_repository.list_for_document(
                document_id,
            )
        )

        amount_paid = Decimal("0.00")

        for allocation in allocations:

            amount_paid += allocation.allocated_amount

        total = Decimal(str(document.total_amount))

        document.amount_paid = amount_paid

        document.amount_due = total - amount_paid

        if document.amount_due <= 0:

            document.payment_status = "paid"

        elif amount_paid > 0:

            document.payment_status = "partial"

        else:

            document.payment_status = "unpaid"

        return await self.document_repository.update_from_integration(
            document.id,
            document,
        )