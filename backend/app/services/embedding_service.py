"""
============================================================
Embedding Service

Responsibilities
----------------
- Generate OpenAI embeddings
- Store document embeddings
- Store vendor embeddings
- Store organization embeddings
- Similarity search helper

No FastAPI.
No business logic.
============================================================
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.domain.document import Document
from app.models.domain.organization import Organization
from app.models.domain.vendor import Vendor

from app.models.domain.embedding import (
    DocumentEmbedding,
    VendorEmbedding,
    OrganizationEmbedding,
)

from app.repositories.ai.embedding_repository import (
    EmbeddingRepository,
)

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
)


class EmbeddingService:
    """
    Generates and persists semantic embeddings.
    """

    MODEL = "text-embedding-3-small"

    def __init__(
        self,
        repository: EmbeddingRepository,
    ) -> None:

        self.repository = repository

    # =====================================================
    # OpenAI
    # =====================================================

    async def generate(
        self,
        text: str,
    ) -> list[float]:

        if not text.strip():
            return []

        response = await client.embeddings.create(
            model=self.MODEL,
            input=text,
        )

        return response.data[0].embedding

    # =====================================================
    # Documents
    # =====================================================

    async def document_embedding(
    self,
    document: Document,
) -> list[float]:

        text = self.document_text(document)

        embedding = await self.generate(text)

        await self.repository.save_document_embedding(
            DocumentEmbedding(
                document_id=document.id,
                org_id=document.org_id,
                embedding=embedding,
                source_text=text,
                model_used=self.MODEL,
            )
        )

        return embedding

    # =====================================================
    # Vendors
    # =====================================================

    async def vendor_embedding(
    self,
    vendor: Vendor,
) -> list[float]:

        text = self.vendor_text(vendor)

        embedding = await self.generate(text)

        await self.repository.save_vendor_embedding(
            VendorEmbedding(
                vendor_id=vendor.id,
                org_id=vendor.org_id,
                embedding=embedding,
                source_text=text,
                model_used=self.MODEL,
            )
        )

        return embedding

    # =====================================================
    # Organization
    # =====================================================

    async def organization_embedding(
    self,
    organization: Organization,
) -> list[float]:

        text = self.organization_text(
            organization,
        )

        embedding = await self.generate(text)

        await self.repository.save_organization_embedding(
            OrganizationEmbedding(
                org_id=organization.id,
                embedding=embedding,
                source_text=text,
                model_used=self.MODEL,
            )
        )

        return embedding

    # =====================================================
    # Text Builders
    # =====================================================

    @staticmethod
    def document_text(
        document: Document,
    ) -> str:

        return "\n".join(
            filter(
                None,
                [
                    document.document_number,
                    document.document_type.value,
                    document.vendor_name,
                    document.currency,
                    str(document.total_amount),
                    document.notes,
                ],
            )
        )

    @staticmethod
    def vendor_text(
        vendor: Vendor,
    ) -> str:

        return "\n".join(
            filter(
                None,
                [
                    vendor.name,
                    vendor.industry,
                    vendor.category,
                    vendor.country,
                    vendor.notes,
                    vendor.ai_summary,
                ],
            )
        )

    @staticmethod
    def organization_text(
        organization: Organization,
    ) -> str:

        return "\n".join(
            filter(
                None,
                [
                    organization.name,
                    organization.industry,
                    organization.company_size,
                    organization.country,
                    organization.currency,
                ],
            )
        )
    # =====================================================
    # Generic Query Embedding
    # =====================================================

    async def create_embedding(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate an embedding for arbitrary text.

        Used by:

        - SearchService
        - CopilotService
        - Semantic retrieval
        - AI memory search
        """

        return await self.generate(text)

    # =====================================================
    # Batch Embeddings
    # =====================================================

    async def create_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts
        in a single OpenAI request.
        """

        texts = [
            text
            for text in texts
            if text and text.strip()
        ]

        if not texts:
            return []

        response = await client.embeddings.create(
            model=self.MODEL,
            input=texts,
        )

        return [
            item.embedding
            for item in response.data
        ]

    # =====================================================
    # Bulk Document Embeddings
    # =====================================================

    async def save_document_embeddings(
        self,
        documents: list[Document],
    ) -> list[DocumentEmbedding]:

        if not documents:
            return []

        texts = [
            self.document_text(document)
            for document in documents
        ]

        vectors = await self.create_embeddings(
            texts,
        )

        embeddings = [
            DocumentEmbedding(
                document_id=document.id,
                org_id=document.org_id,
                embedding=vector,
                source_text=text,
                model_used=self.MODEL,
            )
            for document, text, vector in zip(
                documents,
                texts,
                vectors,
            )
        ]

        await self.repository.save_document_embeddings(
            embeddings,
        )

        return embeddings