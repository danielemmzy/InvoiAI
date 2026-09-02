from __future__ import annotations

from uuid import UUID

from app.mappers.payment_allocation_mapper import (
    PaymentAllocationMapper,
)
from app.models.domain.payment_allocation import (
    PaymentAllocation,
)
from app.repositories.base import BaseRepository


class PaymentAllocationRepository(BaseRepository):

    table_name = "payment_allocations"

    mapper = PaymentAllocationMapper

    async def list_for_payment(
        self,
        payment_id: UUID,
    ) -> list[PaymentAllocation]:

        response = (
            self.table()
            .select("*")
            .eq("payment_id", str(payment_id))
            .execute()
        )

        return self._many(response)

    async def list_for_document(
        self,
        document_id: UUID,
    ) -> list[PaymentAllocation]:

        response = (
            self.table()
            .select("*")
            .eq("document_id", str(document_id))
            .execute()
        )

        return self._many(response)

    async def create_allocation(
        self,
        allocation: PaymentAllocation,
    ) -> PaymentAllocation:

        return await self.create(
            allocation,
        )

    async def delete_allocation(
        self,
        allocation_id: UUID,
    ) -> bool:

        return await self.delete(
            allocation_id,
        )