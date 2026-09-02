"""
============================================================
Vendor Service

Business logic for vendor management.

Responsibilities
----------------
- Vendor CRUD
- Vendor search
- Preferred vendors
- Vendor blocking
- Vendor statistics
- Duplicate prevention

Never talks to Supabase directly.
Never writes SQL.
Repositories handle persistence.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.models.domain.vendor import Vendor
from app.repositories.document.vendor_repository import VendorRepository
from app.schemas.vendor import VendorUpdate


class VendorService:
    """
    Business logic for vendors.
    """

    def __init__(
        self,
        repository: VendorRepository,
    ):
        self.repository = repository

    # =========================================================
    # Create
    # =========================================================

    async def create_vendor(
        self,
        vendor: Vendor,
    ) -> Vendor:
        """
        Create a vendor after validating duplicates.
        """

        existing = await self.repository.get_by_name(
            vendor.org_id,
            vendor.name,
        )

        if existing:
            raise ValueError("Vendor already exists.")

        if vendor.email:
            existing = await self.repository.get_by_email(
                vendor.org_id,
                vendor.email,
            )

            if existing:
                raise ValueError("Vendor email already exists.")

        if vendor.tax_id:
            existing = await self.repository.get_by_tax_id(
                vendor.org_id,
                vendor.tax_id,
            )

            if existing:
                raise ValueError("Vendor tax ID already exists.")

        return await self.repository.create_vendor(
            vendor,
        )

    # =========================================================
    # Retrieve
    # =========================================================

    async def get_vendor(
        self,
        vendor_id: UUID,
    ) -> Vendor | None:

        return await self.repository.get(
            vendor_id,
        )

    async def list_for_org(
        self,
        org_id: UUID,
        limit: int = 50,
    ) -> list[Vendor]:
        """List vendors for an organization through the repository boundary."""
        return await self.repository.list_for_org(
            org_id,
            limit=limit,
        )

    async def search_vendors(
        self,
        org_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[Vendor]:

        return await self.repository.search(
            org_id,
            query,
            limit,
        )

    # =========================================================
    # Update
    # =========================================================

    async def update_vendor(
        self,
        vendor_id: UUID,
        update: VendorUpdate,
    ) -> Vendor:

        vendor = await self.repository.get(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        data = update.model_dump(
            exclude_unset=True,
        )

        return await self.repository.update(
            vendor_id,
            data,
        )

    # =========================================================
    # Delete
    # =========================================================

    async def delete_vendor(
        self,
        vendor_id: UUID,
    ) -> bool:

        vendor = await self.repository.get(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        return await self.repository.delete(
            vendor_id,
        )

    # =========================================================
    # Preferred Vendors
    # =========================================================

    async def list_preferred(
        self,
        org_id: UUID,
    ) -> list[Vendor]:

        return await self.repository.list_preferred(
            org_id,
        )

    async def mark_preferred(
        self,
        vendor_id: UUID,
    ) -> Vendor:

        vendor = await self.repository.get(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        return await self.repository.set_preferred(
            vendor_id,
            True,
        )

    async def remove_preferred(
        self,
        vendor_id: UUID,
    ) -> Vendor:

        vendor = await self.repository.get(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        return await self.repository.set_preferred(
            vendor_id,
            False,
        )

    # =========================================================
    # Blocking
    # =========================================================

    async def list_blocked(
        self,
        org_id: UUID,
    ) -> list[Vendor]:

        return await self.repository.list_blocked(
            org_id,
        )

    async def block_vendor(
        self,
        vendor_id: UUID,
        reason: str,
    ) -> Vendor:

        vendor = await self.repository.get(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        if vendor.is_blocked:
            raise ValueError("Vendor is already blocked.")

        return await self.repository.block(
            vendor_id,
            reason,
        )

    async def unblock_vendor(
        self,
        vendor_id: UUID,
    ) -> Vendor:

        vendor = await self.repository.get(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        if not vendor.is_blocked:
            raise ValueError("Vendor is not blocked.")

        return await self.repository.unblock(
            vendor_id,
        )

    # =========================================================
    # Statistics
    # =========================================================

    async def vendor_statistics(
        self,
        vendor_id: UUID,
    ) -> Vendor:

        vendor = await self.repository.get_statistics(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        return vendor

    async def financial_summary(
        self,
        vendor_id: UUID,
    ) -> Vendor:

        vendor = await self.repository.get_financial_summary(
            vendor_id,
        )

        if vendor is None:
            raise ValueError("Vendor not found.")

        return vendor