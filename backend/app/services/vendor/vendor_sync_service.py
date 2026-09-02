from __future__ import annotations

from app.models.domain.vendor import Vendor
from app.repositories.document.vendor_repository import VendorRepository


class VendorSyncService:
    """
    Shared vendor synchronization service.

    Responsibilities
    ----------------
    • Persist external vendors
    • Prevent duplicates
    • Update existing records
    • Provider-agnostic

    Used by:
        - QuickBooks
        - Xero
        - Sage
        - Future integrations

    No API calls.
    """

    def __init__(self):

        self.repository = VendorRepository()

    # =========================================================
    # Sync
    # =========================================================

    async def sync(
        self,
        vendor: Vendor,
    ) -> Vendor:

        existing = await self.repository.get_by_external_id(
            org_id=vendor.org_id,
            provider=vendor.provider,
            external_id=vendor.external_id,
        )

        if existing:

            vendor.id = existing.id

        return await self.repository.upsert_external(
            vendor,
        )

    # =========================================================
    # Batch Sync
    # =========================================================

    async def sync_many(
        self,
        vendors: list[Vendor],
    ) -> list[Vendor]:

        synced: list[Vendor] = []

        for vendor in vendors:

            synced.append(
                await self.sync(vendor)
            )

        return synced


    # =========================================================
    # Lookup
    # =========================================================

    async def get_by_external_id(
        self,
        *,
        org_id,
        provider,
        external_id: str,
    ):

        return await self.repository.get_by_external_id(
            org_id=org_id,
            provider=provider,
            external_id=external_id,
        )