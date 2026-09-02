from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.mappers.payment_mapper import PaymentMapper
from app.models.domain.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    """
    Repository for payments.

    Responsibilities
    ----------------
    • CRUD
    • External ID lookups
    • Sync persistence
    • Payment queries

    No business logic.
    """

    table_name = "payments"

    mapper = PaymentMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def create_payment(
        self,
        payment: Payment | dict,
    ) -> Payment | None:

        return await self.create(payment)

    async def get_payment(
        self,
        payment_id: UUID,
    ) -> Payment | None:

        return await self.get(payment_id)

    async def update_payment(
        self,
        payment_id: UUID,
        data,
    ) -> Payment | None:

        return await self.update(
            payment_id,
            data,
        )

    async def delete_payment(
        self,
        payment_id: UUID,
    ) -> bool:

        return await self.delete(payment_id)

    # =========================================================
    # External Sync
    # =========================================================

    async def get_external(
        self,
        *,
        org_id: UUID,
        provider: IntegrationProvider,
        external_id: str,
    ) -> Payment | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("provider", provider.value)
            .eq("external_id", external_id)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def upsert_external(
        self,
        payment: Payment | dict,
    ) -> Payment | None:

        response = (
            self.table()
            .upsert(
                self.mapper.to_insert(payment),
                on_conflict="org_id,provider,external_id",
            )
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Queries
    # =========================================================

    async def list_org_payments(
        self,
        org_id: UUID,
        limit: int = 100,
    ) -> list[Payment]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "payment_date",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_document_payments(
        self,
        document_id: UUID,
    ) -> list[Payment]:

        response = (
            self.table()
            .select("*")
            .eq("document_id", str(document_id))
            .order(
                "payment_date",
                desc=True,
            )
            .execute()
        )

        return self._many(response)

    async def list_vendor_payments(
        self,
        vendor_id: UUID,
    ) -> list[Payment]:

        response = (
            self.table()
            .select("*")
            .eq("vendor_id", str(vendor_id))
            .order(
                "payment_date",
                desc=True,
            )
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Sync
    # =========================================================

    async def mark_synced(
        self,
        payment_id: UUID,
    ) -> Payment | None:

        return await self.update_payment(
            payment_id,
            {
                "synced_at": datetime.now(UTC),
            },
        )

    async def update_external_timestamp(
        self,
        payment_id: UUID,
        modified_at,
    ) -> Payment | None:

        return await self.update_payment(
            payment_id,
            {
                "last_modified_external": modified_at,
            },
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def exists_external(
        self,
        *,
        org_id: UUID,
        provider: IntegrationProvider,
        external_id: str,
    ) -> bool:

        response = (
            self.table()
            .select("id")
            .eq("org_id", str(org_id))
            .eq("provider", provider.value)
            .eq("external_id", external_id)
            .limit(1)
            .execute()
        )

        return bool(response.data)