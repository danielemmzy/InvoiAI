from __future__ import annotations

from datetime import UTC, datetime, date
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.mappers.purchase_order_mapper import PurchaseOrderMapper
from app.models.domain.purchase_order import PurchaseOrder
from app.repositories.base import BaseRepository


class PurchaseOrderRepository(BaseRepository):
    """
    Repository for purchase_orders.

    Owns persistence for Purchase Orders only.

    No business logic.
    """

    table_name = "purchase_orders"

    mapper = PurchaseOrderMapper

    # =====================================================
    # CRUD
    # =====================================================

    async def create_purchase_order(
        self,
        purchase_order: PurchaseOrder | dict,
    ) -> PurchaseOrder | None:

        return await self.create(purchase_order)

    async def get_purchase_order(
        self,
        purchase_order_id: UUID,
    ) -> PurchaseOrder | None:

        return await self.get(purchase_order_id)

    async def update_purchase_order(
        self,
        purchase_order_id: UUID,
        values,
    ) -> PurchaseOrder | None:

        if isinstance(values, dict):
            values["updated_at"] = datetime.now(UTC)

        return await self.update(
            purchase_order_id,
            values,
        )

    async def delete_purchase_order(
        self,
        purchase_order_id: UUID,
    ) -> bool:

        return await self.delete(purchase_order_id)

    # =====================================================
    # Internal Lookup
    # =====================================================

    async def get_by_number(
        self,
        *,
        org_id: UUID,
        po_number: str,
    ) -> PurchaseOrder | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("po_number", po_number)
            .limit(1)
            .execute()
        )

        return self._one(response)

    # =====================================================
    # External Lookup
    # =====================================================

    async def get_by_external_id(
        self,
        *,
        org_id: UUID,
        provider: IntegrationProvider,
        external_id: str,
    ) -> PurchaseOrder | None:

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

    # =====================================================
    # Lists
    # =====================================================

    async def list_open(
        self,
        *,
        org_id: UUID,
    ) -> list[PurchaseOrder]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_open", True)
            .order(
                "issued_date",
                desc=True,
            )
            .execute()
        )

        return self._many(response)

    async def list_purchase_orders(
        self,
        org_id: UUID,
        *,
        vendor_id: UUID | None = None,
        is_open: bool | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 25,
        offset: int = 0,
    ):
        query = (
            self.table()
            .select("*, vendors(name)", count="exact")
            .eq("org_id", str(org_id))
        )

        if vendor_id is not None:
            query = query.eq("vendor_id", str(vendor_id))
        if is_open is not None:
            query = query.eq("is_open", is_open)
        if search:
            query = query.ilike("po_number", f"%{search}%")
        if date_from is not None:
            query = query.gte("issued_date", date_from.isoformat())
        if date_to is not None:
            query = query.lte("issued_date", date_to.isoformat())

        response = (
            query.order("issued_date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return response.data or [], response.count or 0

    async def list_vendor_purchase_orders(
        self,
        *,
        org_id: UUID,
        vendor_id: UUID,
    ) -> list[PurchaseOrder]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("vendor_id", str(vendor_id))
            .order(
                "issued_date",
                desc=True,
            )
            .execute()
        )

        return self._many(response)

    # =====================================================
    # Matching
    # =====================================================

    async def match_document(
        self,
        *,
        org_id: UUID,
        po_number: str,
    ) -> PurchaseOrder | None:

        return await self.get_by_number(
            org_id=org_id,
            po_number=po_number,
        )

    # =====================================================
    # External Upsert
    # =====================================================

    async def upsert_external(
        self,
        purchase_order: PurchaseOrder,
    ) -> PurchaseOrder | None:
        """
        Create or update a Purchase Order coming from an
        external provider (QuickBooks, Xero, Sage, etc.).

        Matching priority:

        1. provider + external_id
        2. org_id + po_number
        """

        #
        # Match using provider + external_id
        #

        existing = None

        if purchase_order.external_id and purchase_order.provider:

            existing = await self.get_by_external_id(
                org_id=purchase_order.org_id,
                provider=purchase_order.provider,
                external_id=purchase_order.external_id,
            )

        #
        # Fallback to PO number
        #

        if existing is None and purchase_order.external_id is None:

            existing = await self.get_by_number(
                org_id=purchase_order.org_id,
                po_number=purchase_order.po_number,
            )

        #
        # Update existing
        #

        if existing:

            values = self.mapper.to_update(
                purchase_order,
            )

            values.pop("id", None)
            values.pop("created_at", None)

            values["updated_at"] = datetime.now(UTC)

            return await self.update_purchase_order(
                existing.id,
                values,
            )

        #
        # Create new
        #

        return await self.create_purchase_order(
            purchase_order,
        )
