"""
============================================================
Embedding Repository

Handles:

- document_embeddings
- organization_embeddings
- vendor_embeddings

Repositories only persist vectors.

Embedding generation belongs in EmbeddingService.
============================================================
"""

from typing import Any

from app.repositories.base import BaseRepository
from supabase import SyncQueryBuilder


class EmbeddingRepository(BaseRepository):

    DOCUMENT_TABLE = "document_embeddings"
    ORGANIZATION_TABLE = "organization_embeddings"
    VENDOR_TABLE = "vendor_embeddings"

    def document_embeddings(self):
        return self.db.table(self.DOCUMENT_TABLE)

    def organization_embeddings(self):
        return self.db.table(self.ORGANIZATION_TABLE)

    def vendor_embeddings(self):
        return self.db.table(self.VENDOR_TABLE)
    
        # =========================================================
    # Internal
    # =========================================================

    @staticmethod
    def _first(result) -> dict | None:
        return result.data[0] if result.data else None

    @staticmethod
    def _rows(result) -> list[dict]:
        return result.data or []

    def _table(
        self,
        table_name: str,
    ) -> SyncQueryBuilder:
        return self.db.table(table_name)
    
        # =========================================================
    # Generic CRUD
    # =========================================================

    async def _create(
        self,
        table: str,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self._table(table)
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def _get(
        self,
        table: str,
        column: str,
        value: str,
    ) -> dict | None:

        result = (
            self._table(table)
            .select("*")
            .eq(column, value)
            .limit(1)
            .execute()
        )

        return self._first(result)

    async def _update(
        self,
        table: str,
        column: str,
        value: str,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self._table(table)
            .update(values)
            .eq(column, value)
            .execute()
        )

        return result.data[0]

    async def _delete(
        self,
        table: str,
        column: str,
        value: str,
    ) -> None:

        (
            self._table(table)
            .delete()
            .eq(column, value)
            .execute()
        )

        # =========================================================
    # Document Embeddings
    # =========================================================

    async def create_document_embedding(
        self,
        values: dict[str, Any],
    ) -> dict:
        return await self._create(
            self.DOCUMENT_TABLE,
            values,
        )

    async def get_document_embedding(
        self,
        document_id: str,
    ) -> dict | None:
        """
        Uses document_embeddings_document_id_key.
        """
        return await self._get(
            self.DOCUMENT_TABLE,
            "document_id",
            document_id,
        )

    async def update_document_embedding(
        self,
        document_id: str,
        values: dict[str, Any],
    ) -> dict:
        return await self._update(
            self.DOCUMENT_TABLE,
            "document_id",
            document_id,
            values,
        )

    async def delete_document_embedding(
        self,
        document_id: str,
    ) -> None:
        await self._delete(
            self.DOCUMENT_TABLE,
            "document_id",
            document_id,
        )

    async def document_embedding_exists(
        self,
        document_id: str,
    ) -> bool:
        return (
            await self.get_document_embedding(document_id)
        ) is not None
    
        # =========================================================
    # Organization Embeddings
    # =========================================================

    async def create_organization_embedding(
        self,
        values: dict[str, Any],
    ) -> dict:
        return await self._create(
            self.ORGANIZATION_TABLE,
            values,
        )

    async def get_organization_embedding(
        self,
        org_id: str,
    ) -> dict | None:
        """
        Uses organization_embeddings_org_id_key.
        """
        return await self._get(
            self.ORGANIZATION_TABLE,
            "org_id",
            org_id,
        )

    async def update_organization_embedding(
        self,
        org_id: str,
        values: dict[str, Any],
    ) -> dict:
        return await self._update(
            self.ORGANIZATION_TABLE,
            "org_id",
            org_id,
            values,
        )

    async def delete_organization_embedding(
        self,
        org_id: str,
    ) -> None:
        await self._delete(
            self.ORGANIZATION_TABLE,
            "org_id",
            org_id,
        )

    async def organization_embedding_exists(
        self,
        org_id: str,
    ) -> bool:
        return (
            await self.get_organization_embedding(org_id)
        ) is not None
    
        # =========================================================
    # Vendor Embeddings
    # =========================================================

    async def create_vendor_embedding(
        self,
        values: dict[str, Any],
    ) -> dict:
        return await self._create(
            self.VENDOR_TABLE,
            values,
        )

    async def get_vendor_embedding(
        self,
        vendor_id: str,
    ) -> dict | None:
        """
        Uses vendor_embeddings_vendor_id_key.
        """
        return await self._get(
            self.VENDOR_TABLE,
            "vendor_id",
            vendor_id,
        )

    async def update_vendor_embedding(
        self,
        vendor_id: str,
        values: dict[str, Any],
    ) -> dict:
        return await self._update(
            self.VENDOR_TABLE,
            "vendor_id",
            vendor_id,
            values,
        )

    async def delete_vendor_embedding(
        self,
        vendor_id: str,
    ) -> None:
        await self._delete(
            self.VENDOR_TABLE,
            "vendor_id",
            vendor_id,
        )

    async def vendor_embedding_exists(
        self,
        vendor_id: str,
    ) -> bool:
        return (
            await self.get_vendor_embedding(vendor_id)
        ) is not None