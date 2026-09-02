from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.mappers.memory_mapper import (
    DocumentMemoryMapper,
    OrganizationMemoryMapper,
    VendorMemoryMapper,
)
from app.models.domain.memory import (
    DocumentMemory,
    OrganizationMemory,
    VendorMemory,
)
from app.repositories.base import BaseRepository


# ============================================================
# Document Memory
# ============================================================


class DocumentMemoryRepository(BaseRepository):
    """
    Repository for document_memory.
    """

    table_name = "document_memory"
    mapper = DocumentMemoryMapper

    async def create_memory(
        self,
        memory: DocumentMemory | dict,
    ) -> DocumentMemory | None:
        return await self.create(memory)

    async def get_memory(
        self,
        memory_id: UUID,
    ) -> DocumentMemory | None:
        return await self.get(memory_id)

    async def update_memory(
        self,
        memory_id: UUID,
        data,
    ) -> DocumentMemory | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            memory_id,
            data,
        )

    async def delete_memory(
        self,
        memory_id: UUID,
    ) -> bool:
        return await self.delete(memory_id)

    async def get_document_memory(
        self,
        document_id: UUID,
    ) -> DocumentMemory | None:

        response = (
            self.table()
            .select("*")
            .eq("document_id", str(document_id))
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_organization_memory(
        self,
        org_id: UUID,
    ) -> list[DocumentMemory]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("updated_at", desc=True)
            .execute()
        )

        return self._many(response)


# ============================================================
# Organization Memory
# ============================================================


class OrganizationMemoryRepository(BaseRepository):
    """
    Repository for organization_memory.
    """

    table_name = "organization_memory"
    mapper = OrganizationMemoryMapper

    async def create_memory(
        self,
        memory: OrganizationMemory | dict,
    ) -> OrganizationMemory | None:
        return await self.create(memory)

    async def get_memory(
        self,
        memory_id: UUID,
    ) -> OrganizationMemory | None:
        return await self.get(memory_id)

    async def update_memory(
        self,
        memory_id: UUID,
        data,
    ) -> OrganizationMemory | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            memory_id,
            data,
        )

    async def delete_memory(
        self,
        memory_id: UUID,
    ) -> bool:
        return await self.delete(memory_id)

    async def get_org_memory(
        self,
        org_id: UUID,
    ) -> OrganizationMemory | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .limit(1)
            .execute()
        )

        return self._one(response)


# ============================================================
# Vendor Memory
# ============================================================


class VendorMemoryRepository(BaseRepository):
    """
    Repository for vendor_memory.
    """

    table_name = "vendor_memory"
    mapper = VendorMemoryMapper

    async def create_memory(
        self,
        memory: VendorMemory | dict,
    ) -> VendorMemory | None:
        return await self.create(memory)

    async def get_memory(
        self,
        memory_id: UUID,
    ) -> VendorMemory | None:
        return await self.get(memory_id)

    async def update_memory(
        self,
        memory_id: UUID,
        data,
    ) -> VendorMemory | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            memory_id,
            data,
        )

    async def delete_memory(
        self,
        memory_id: UUID,
    ) -> bool:
        return await self.delete(memory_id)

    async def get_vendor_memory(
        self,
        vendor_id: UUID,
    ) -> VendorMemory | None:

        response = (
            self.table()
            .select("*")
            .eq("vendor_id", str(vendor_id))
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_organization_memory(
        self,
        org_id: UUID,
    ) -> list[VendorMemory]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("updated_at", desc=True)
            .execute()
        )

        return self._many(response)