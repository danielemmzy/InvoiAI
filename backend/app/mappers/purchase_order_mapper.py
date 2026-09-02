from __future__ import annotations

from decimal import Decimal

from app.core.enum.database import IntegrationProvider
from app.models.domain.purchase_order import PurchaseOrder


class PurchaseOrderMapper:
    """
    Maps PurchaseOrder domain objects
    to and from database rows.
    """

    @staticmethod
    def to_domain(row: dict) -> PurchaseOrder:

        return PurchaseOrder(
            id=row["id"],
            org_id=row["org_id"],
            vendor_id=row.get("vendor_id"),
            po_number=row["po_number"],
            description=row.get("description"),
            amount=Decimal(str(row.get("amount", 0))),
            currency=row.get("currency", "USD"),
            issued_date=row.get("issued_date"),
            expiry_date=row.get("expiry_date"),
            is_open=row.get("is_open", True),
            matched_amount=Decimal(
                str(row.get("matched_amount", 0))
            ),
            created_by=row.get("created_by"),
            provider=(
                IntegrationProvider(row["provider"])
                if row.get("provider")
                else None
            ),
            external_id=row.get("external_id"),
            status=row.get("status"),
            synced_at=row.get("synced_at"),
            last_modified_external=row.get(
                "last_modified_external"
            ),
            metadata=row.get("metadata") or {},
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def to_row(po: PurchaseOrder) -> dict:

        return {
            "id": str(po.id),
            "org_id": str(po.org_id),
            "vendor_id": (
                str(po.vendor_id)
                if po.vendor_id
                else None
            ),
            "po_number": po.po_number,
            "description": po.description,
            "amount": float(po.amount),
            "currency": po.currency,
            "issued_date": po.issued_date,
            "expiry_date": po.expiry_date,
            "is_open": po.is_open,
            "matched_amount": float(po.matched_amount),
            "created_by": (
                str(po.created_by)
                if po.created_by
                else None
            ),
            "provider": (
                po.provider.value
                if po.provider
                else None
            ),
            "external_id": po.external_id,
            "status": po.status,
            "synced_at": po.synced_at,
            "last_modified_external": (
                po.last_modified_external
            ),
            "metadata": po.metadata,
            "created_at": po.created_at,
            "updated_at": po.updated_at,
        }