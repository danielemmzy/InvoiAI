from __future__ import annotations

from abc import ABC
from uuid import UUID


class ExternalSyncMixin(ABC):
    """
    Mixin providing repository operations used by all
    external integrations.

    Every repository storing provider-owned resources
    (vendors, customers, invoices, purchase orders,
    payments...) should inherit this mixin.
    """

    async def get_by_external_id(
        self,
        *,
        org_id: UUID,
        provider: str,
        external_id: str,
    ):
        raise NotImplementedError

    async def exists_external(
        self,
        *,
        org_id: UUID,
        provider: str,
        external_id: str,
    ) -> bool:

        record = await self.get_by_external_id(
            org_id=org_id,
            provider=provider,
            external_id=external_id,
        )

        return record is not None

    async def create_from_integration(
        self,
        model,
    ):
        raise NotImplementedError

    async def update_from_integration(
        self,
        record_id: UUID,
        model,
    ):
        raise NotImplementedError

    async def upsert_from_integration(
        self,
        *,
        org_id: UUID,
        provider: str,
        external_id: str,
        model,
    ):
        """
        Default implementation shared by all repositories.
        """

        existing = await self.get_by_external_id(
            org_id=org_id,
            provider=provider,
            external_id=external_id,
        )

        if existing:
            return await self.update_from_integration(
                existing.id,
                model,
            )

        return await self.create_from_integration(
            model,
        )