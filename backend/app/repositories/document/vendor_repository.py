"""
============================================================
Vendor Repository

Responsible ONLY for vendor persistence.

No business logic.
No AI.
No OCR.

============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.mappers.vendor_mapper import VendorMapper
from app.models.domain.vendor import Vendor
from app.repositories.base import BaseRepository
from app.repositories.mixins.external_sync import ExternalSyncMixin
from datetime import UTC, datetime


class VendorRepository(BaseRepository, ExternalSyncMixin):
    """
    Repository for vendors table.
    """

    table_name = "vendors"

    mapper = VendorMapper

    # =========================================================
    # Lookups
    # =========================================================

    async def get_by_name(
        self,
        org_id: UUID,
        name: str,
    ) -> Vendor | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .ilike("name", name)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def get_by_email(
        self,
        org_id: UUID,
        email: str,
    ) -> Vendor | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("email", email)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def get_by_tax_id(
        self,
        org_id: UUID,
        tax_id: str,
    ) -> Vendor | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("tax_id", tax_id)
            .limit(1)
            .execute()
        )

        return self._one(response)

    # =========================================================
    # External Integrations
    # =========================================================

    async def get_by_external_id(
        self,
        *,
        org_id: UUID,
        provider: str,
        external_id: str,
    ) -> Vendor | None:
        """
        Retrieve a vendor imported from an external system.
        """

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("provider", provider)
            .eq("external_id", external_id)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def upsert_external(
        self,
        vendor: Vendor,
    ) -> Vendor:

        existing = await self.get_by_external_id(
            org_id=vendor.org_id,
            provider=vendor.provider.value,
            external_id=vendor.external_id,
        )

        if existing:

            response = (
                self.table()
                .update(
                    {
                        "name": vendor.name,
                        "email": vendor.email,
                        "phone": vendor.phone,
                        "website": vendor.website,
                        "tax_id": vendor.tax_id,
                        "address": vendor.address,
                        "currency": vendor.currency,
                        "provider": vendor.provider.value,
                        "external_id": vendor.external_id,
                        "metadata": vendor.metadata,
                        "is_active": vendor.is_active,
                        "last_modified_external": vendor.last_modified_external,
                        "synced_at": vendor.synced_at,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                .eq("id", str(existing.id))
                .execute()
            )

            return self._one(response)

        return await self.create(vendor)

    async def create_from_integration(
        self,
        vendor: Vendor,
    ) -> Vendor:

        return await self.create(vendor)

    async def update_from_integration(
        self,
        vendor_id: UUID,
        vendor: Vendor,
    ) -> Vendor | None:

        return await self.update(
            vendor_id,
            vendor,
        )

    async def mark_synced(
        self,
        *,
        vendor_id: UUID,
    ) -> Vendor | None:

        response = (
            self.table()
            .update(
                {
                    "last_synced_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(vendor_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Search
    # =========================================================

    async def search(
        self,
        org_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[Vendor]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .ilike("name", f"%{query}%")
            .order(
                "name",
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Preferred
    # =========================================================

    async def list_preferred(
        self,
        org_id: UUID,
    ) -> list[Vendor]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_preferred", True)
            .order(
                "name",
            )
            .execute()
        )

        return self._many(response)

    async def set_preferred(
        self,
        vendor_id: UUID,
        preferred: bool,
    ) -> Vendor | None:

        response = (
            self.table()
            .update(
                {
                    "is_preferred": preferred,
                }
            )
            .eq("id", str(vendor_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Blocked
    # =========================================================

    async def list_blocked(
        self,
        org_id: UUID,
    ) -> list[Vendor]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_blocked", True)
            .order(
                "name",
            )
            .execute()
        )

        return self._many(response)

    async def block(
        self,
        vendor_id: UUID,
        reason: str,
    ) -> Vendor | None:

        response = (
            self.table()
            .update(
                {
                    "is_blocked": True,
                    "blocked_reason": reason,
                }
            )
            .eq("id", str(vendor_id))
            .execute()
        )

        return self._one(response)

    async def unblock(
        self,
        vendor_id: UUID,
    ) -> Vendor | None:

        response = (
            self.table()
            .update(
                {
                    "is_blocked": False,
                    "blocked_reason": None,
                }
            )
            .eq("id", str(vendor_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Statistics
    # =========================================================

    async def get_statistics(
        self,
        vendor_id: UUID,
    ) -> Vendor | None:

        response = self.table().select("""
                invoice_count,
                receipt_count,
                total_document_count,
                total_spend,
                average_spend,
                risk_score,
                risk_level
                """).eq("id", str(vendor_id)).single().execute()

        return self._one(response)

    async def get_financial_summary(
        self,
        vendor_id: UUID,
    ) -> Vendor | None:

        response = self.table().select("*").eq("id", str(vendor_id)).single().execute()

        return self._one(response)

    # =========================================================
    # Analytics
    # =========================================================

    from datetime import UTC, datetime, timedelta

    async def vendor_count(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .execute()
        )

        return response.count or 0

    async def preferred_vendor_count(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq("is_preferred", True)
            .execute()
        )

        return response.count or 0

    async def blocked_vendor_count(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq("is_blocked", True)
            .execute()
        )

        return response.count or 0

    async def new_vendors_this_month(
        self,
        org_id: UUID,
    ) -> int:

        start = (
            datetime.now(UTC)
            .replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            .isoformat()
        )

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .gte("created_at", start)
            .execute()
        )

        return response.count or 0

    async def top_vendors_by_spend(
        self,
        org_id: UUID,
        limit: int = 10,
    ) -> list[Vendor]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "total_spend",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def top_vendors_by_documents(
        self,
        org_id: UUID,
        limit: int = 10,
    ) -> list[Vendor]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "total_document_count",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def highest_risk_vendors(
        self,
        org_id: UUID,
        limit: int = 10,
    ) -> list[Vendor]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "risk_score",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def vendor_spend_by_month(
        self,
        org_id: UUID,
    ) -> list[Vendor]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "total_spend",
                desc=True,
            )
            .execute()
        )

        return self._many(response)


    async def list_for_org(self, org_id: UUID, *, limit: int = 100) -> list[Vendor]:
        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("updated_at", desc=False)
            .limit(limit)
            .execute()
        )
        return self._many(response)

    async def list_all(self, *, limit: int = 100) -> list[Vendor]:
        response = (
            self.table()
            .select("*")
            .order("updated_at", desc=False)
            .limit(limit)
            .execute()
        )
        return self._many(response)
