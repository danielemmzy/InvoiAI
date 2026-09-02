from __future__ import annotations

from typing import Type
from uuid import UUID

from app.mappers.embedding_mapper import (
    DocumentEmbeddingMapper,
    OrganizationEmbeddingMapper,
    VendorEmbeddingMapper,
)
from app.models.domain.embedding import (
    BaseEmbedding,
    DocumentEmbedding,
    OrganizationEmbedding,
    VendorEmbedding,
)
from app.repositories.base import BaseRepository
from app.schemas.embedding import DocumentEmbeddingMatch, OrganizationEmbeddingMatch, OrganizationEmbeddingMatch, VendorEmbeddingMatch


class EmbeddingRepository(BaseRepository):
    """
    Repository for embedding persistence.

    Owns:

    - document_embeddings
    - vendor_embeddings
    - organization_embeddings
    """

    table_name = "document_embeddings"
    mapper = DocumentEmbeddingMapper

    DOCUMENT_TABLE = "document_embeddings"
    VENDOR_TABLE = "vendor_embeddings"
    ORGANIZATION_TABLE = "organization_embeddings"

    # =========================================================
    # Internal
    # =========================================================

    def _query(
        self,
        table: str,
    ):
        return self.db.table(table)

    async def _create(
        self,
        table: str,
        mapper,
        data,
    ):
        response = self._query(table).insert(mapper.to_insert(data)).execute()

        row = self.raw(response)

        return mapper.to_domain(row) if row else None

    async def _get(
        self,
        table: str,
        mapper,
        column: str,
        value: UUID,
    ):
        response = (
            self._query(table).select("*").eq(column, str(value)).limit(1).execute()
        )

        row = self.raw(response)

        return mapper.to_domain(row) if row else None

    async def _update(
        self,
        table: str,
        mapper,
        column: str,
        value: UUID,
        data,
    ):
        response = (
            self._query(table)
            .update(mapper.to_update(data))
            .eq(column, str(value))
            .execute()
        )

        row = self.raw(response)

        return mapper.to_domain(row) if row else None

    async def _delete(
        self,
        table: str,
        column: str,
        value: UUID,
    ) -> bool:

        (self._query(table).delete().eq(column, str(value)).execute())

        return True

    async def _exists(
        self,
        table: str,
        column: str,
        value: UUID,
    ) -> bool:

        response = (
            self._query(table).select("id").eq(column, str(value)).limit(1).execute()
        )

        return bool(response.data)

    # =========================================================
    # Document Embeddings
    # =========================================================

    async def create_document_embedding(
        self,
        embedding: DocumentEmbedding | dict,
    ) -> DocumentEmbedding | None:

        return await self._create(
            self.DOCUMENT_TABLE,
            DocumentEmbeddingMapper,
            embedding,
        )

    async def get_document_embedding(
        self,
        document_id: UUID,
    ) -> DocumentEmbedding | None:

        return await self._get(
            self.DOCUMENT_TABLE,
            DocumentEmbeddingMapper,
            "document_id",
            document_id,
        )

    async def update_document_embedding(
        self,
        document_id: UUID,
        values,
    ) -> DocumentEmbedding | None:

        return await self._update(
            self.DOCUMENT_TABLE,
            DocumentEmbeddingMapper,
            "document_id",
            document_id,
            values,
        )

    async def delete_document_embedding(
        self,
        document_id: UUID,
    ) -> bool:

        return await self._delete(
            self.DOCUMENT_TABLE,
            "document_id",
            document_id,
        )

    async def document_embedding_exists(
        self,
        document_id: UUID,
    ) -> bool:

        return await self._exists(
            self.DOCUMENT_TABLE,
            "document_id",
            document_id,
        )

    # =========================================================
    # Vendor Embeddings
    # =========================================================

    async def create_vendor_embedding(
        self,
        embedding: VendorEmbedding | dict,
    ) -> VendorEmbedding | None:

        return await self._create(
            self.VENDOR_TABLE,
            VendorEmbeddingMapper,
            embedding,
        )

    async def get_vendor_embedding(
        self,
        vendor_id: UUID,
    ) -> VendorEmbedding | None:

        return await self._get(
            self.VENDOR_TABLE,
            VendorEmbeddingMapper,
            "vendor_id",
            vendor_id,
        )

    async def update_vendor_embedding(
        self,
        vendor_id: UUID,
        values,
    ) -> VendorEmbedding | None:

        return await self._update(
            self.VENDOR_TABLE,
            VendorEmbeddingMapper,
            "vendor_id",
            vendor_id,
            values,
        )

    async def delete_vendor_embedding(
        self,
        vendor_id: UUID,
    ) -> bool:

        return await self._delete(
            self.VENDOR_TABLE,
            "vendor_id",
            vendor_id,
        )

    async def vendor_embedding_exists(
        self,
        vendor_id: UUID,
    ) -> bool:

        return await self._exists(
            self.VENDOR_TABLE,
            "vendor_id",
            vendor_id,
        )

    # =========================================================
    # Organization Embeddings
    # =========================================================

    async def create_organization_embedding(
        self,
        embedding: OrganizationEmbedding | dict,
    ) -> OrganizationEmbedding | None:

        return await self._create(
            self.ORGANIZATION_TABLE,
            OrganizationEmbeddingMapper,
            embedding,
        )

    async def get_organization_embedding(
        self,
        org_id: UUID,
    ) -> OrganizationEmbedding | None:

        return await self._get(
            self.ORGANIZATION_TABLE,
            OrganizationEmbeddingMapper,
            "org_id",
            org_id,
        )

    async def update_organization_embedding(
        self,
        org_id: UUID,
        values,
    ) -> OrganizationEmbedding | None:

        return await self._update(
            self.ORGANIZATION_TABLE,
            OrganizationEmbeddingMapper,
            "org_id",
            org_id,
            values,
        )

    async def delete_organization_embedding(
        self,
        org_id: UUID,
    ) -> bool:

        return await self._delete(
            self.ORGANIZATION_TABLE,
            "org_id",
            org_id,
        )

    async def organization_embedding_exists(
        self,
        org_id: UUID,
    ) -> bool:

        return await self._exists(
            self.ORGANIZATION_TABLE,
            "org_id",
            org_id,
        )

    # =========================================================
    # Semantic Search
    # =========================================================

    async def search_document_context(
        self,
        *,
        org_id: UUID,
        embedding: list[float],
        limit: int = 8,
    ) -> list[DocumentEmbeddingMatch]:
        """
        Semantic search across document embeddings.

        Requires PostgreSQL RPC:
            match_document_embeddings
        """

        response = self.db.rpc(
            "match_document_embeddings",
            {
                "p_org_id": str(org_id),
                "query_embedding": embedding,
                "match_count": limit,
            },
        ).execute()

        return [
            DocumentEmbeddingMatch.model_validate(item)
            for item in (response.data or [])
        ]

    async def search_vendor_context(
        self,
        *,
        org_id: UUID,
        embedding: list[float],
        limit: int = 5,
    ) -> list[VendorEmbeddingMatch]:

        response = self.db.rpc(
            "match_vendor_embeddings",
            {
                "p_org_id": str(org_id),
                "query_embedding": embedding,
                "match_count": limit,
            },
        ).execute()

        return [
            VendorEmbeddingMatch.model_validate(item) for item in (response.data or [])
        ]

    async def search_organization_context(
        self,
        *,
        org_id: UUID,
        embedding: list[float],
        limit: int = 3,
    ) -> list[OrganizationEmbeddingMatch]:

        response = (
            self.db.rpc(
                "match_organization_embeddings",
                {
                    "p_org_id": str(org_id),
                    "query_embedding": embedding,
                    "match_count": limit,
                },
            )
            .execute()
        )

        return [
            OrganizationEmbeddingMatch.model_validate(item)
            for item in (response.data or [])
        ]

    # =========================================================
    # Upsert Helpers
    # =========================================================

    async def save_document_embedding(
        self,
        embedding: DocumentEmbedding | dict,
    ) -> DocumentEmbedding | None:

        document_id = (
            embedding.document_id
            if isinstance(embedding, DocumentEmbedding)
            else embedding["document_id"]
        )

        exists = await self.document_embedding_exists(
            document_id,
        )

        if exists:
            return await self.update_document_embedding(
                document_id,
                embedding,
            )

        return await self.create_document_embedding(
            embedding,
        )

    async def save_vendor_embedding(
        self,
        embedding: VendorEmbedding | dict,
    ) -> VendorEmbedding | None:

        vendor_id = (
            embedding.vendor_id
            if isinstance(embedding, VendorEmbedding)
            else embedding["vendor_id"]
        )

        exists = await self.vendor_embedding_exists(
            vendor_id,
        )

        if exists:
            return await self.update_vendor_embedding(
                vendor_id,
                embedding,
            )

        return await self.create_vendor_embedding(
            embedding,
        )

    async def save_organization_embedding(
        self,
        embedding: OrganizationEmbedding | dict,
    ) -> OrganizationEmbedding | None:

        org_id = (
            embedding.org_id
            if isinstance(embedding, OrganizationEmbedding)
            else embedding["org_id"]
        )

        exists = await self.organization_embedding_exists(
            org_id,
        )

        if exists:
            return await self.update_organization_embedding(
                org_id,
                embedding,
            )

        return await self.create_organization_embedding(
            embedding,
        )

    # =========================================================
    # Bulk Save
    # =========================================================

    async def save_document_embeddings(
        self,
        embeddings: list[DocumentEmbedding],
    ) -> list[DocumentEmbedding]:

        if not embeddings:
            return []

        payload = [
            DocumentEmbeddingMapper.to_insert(
                embedding,
            )
            for embedding in embeddings
        ]

        response = (
            self.db
            .table(self.DOCUMENT_TABLE)
            .upsert(
                payload,
                on_conflict="document_id",
            )
            .execute()
        )

        return [
            DocumentEmbeddingMapper.to_domain(row)
            for row in (response.data or [])
        ]
