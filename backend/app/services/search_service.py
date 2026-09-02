"""
============================================================
Search Service

Responsibilities
----------------
- Semantic document search
- Semantic vendor search
- Organization memory retrieval
- AI context assembly

No FastAPI.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.repositories.ai.embedding_repository import EmbeddingRepository
from app.services.embedding_service import EmbeddingService


class SearchService:
    """
    Semantic retrieval service.

    Owns all vector search operations used by AI services.
    """

    def __init__(
        self,
        embedding_repository: EmbeddingRepository | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.embedding_repository = embedding_repository or EmbeddingRepository()
        self.embedding_service = embedding_service or EmbeddingService(self.embedding_repository)

    async def create_embedding(self, text: str) -> list[float]:
        return await self.embedding_service.generate(text)

    # =========================================================
    # Document Search
    # =========================================================

    async def search_documents(
        self,
        *,
        org_id: UUID,
        query: str,
        limit: int = 8,
    ) -> list[dict]:
        """
        Perform semantic search across document embeddings.
        """

        query_embedding = await self.embedding_service.create_embedding(
            query,
        )

        return await self.embedding_repository.search_document_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=limit,
        )

    # =========================================================
    # Vendor Search
    # =========================================================

    async def search_vendors(
        self,
        *,
        org_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Perform semantic search across vendor memory.
        """

        query_embedding = await self.embedding_service.create_embedding(
            query,
        )

        return await self.embedding_repository.search_vendor_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=limit,
        )

    # =========================================================
    # Organization Search
    # =========================================================

    async def search_organization(
        self,
        *,
        org_id: UUID,
        query: str,
    ) -> list[dict]:
        """
        Search organization memory.
        """

        query_embedding = await self.embedding_service.create_embedding(
            query,
        )

        return await self.embedding_repository.search_organization_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=3,
        )

    # =========================================================
    # Combined Search
    # =========================================================

    async def search_all(
        self,
        *,
        org_id: UUID,
        query: str,
        document_limit: int = 8,
        vendor_limit: int = 5,
        organization_limit: int = 1,
    ) -> dict:
        """
        Perform semantic search across every memory source.

        Returns a unified search result.
        """

        documents = await self.search_documents(
            org_id=org_id,
            query=query,
            limit=document_limit,
        )

        vendors = await self.search_vendors(
            org_id=org_id,
            query=query,
            limit=vendor_limit,
        )

        organization = await self.search_organization(
            org_id=org_id,
            query=query,
        )

        return {
            "documents": documents,
            "vendors": vendors,
            "organization": organization[:organization_limit],
        }

    # =========================================================
    # AI Context Builder
    # =========================================================

    @staticmethod
    def build_context(
        *,
        documents: list[dict],
        vendors: list[dict],
        organization: list[dict],
    ) -> str:
        """
        Build a single context string suitable for GPT.
        """

        sections: list[str] = []

        if organization:

            sections.append(
                "## Organization Memory"
            )

            for item in organization:

                text = item.get(
                    "source_text",
                    "",
                ).strip()

                if text:
                    sections.append(text)

        if vendors:

            sections.append(
                "## Vendor Memory"
            )

            for item in vendors:

                text = item.get(
                    "source_text",
                    "",
                ).strip()

                if text:
                    sections.append(text)

        if documents:

            sections.append(
                "## Relevant Documents"
            )

            for item in documents:

                text = item.get(
                    "source_text",
                    "",
                ).strip()

                if text:
                    sections.append(text)

        return "\n\n".join(sections)

        # =========================================================
    # Context Retrieval
    # =========================================================

    async def retrieve_context(
        self,
        *,
        org_id: UUID,
        query: str,
        document_limit: int = 8,
        vendor_limit: int = 5,
        organization_limit: int = 1,
    ) -> str:
        """
        Retrieve semantic context for AI.

        Performs semantic searches across all memory
        sources and returns a single prompt-ready context.
        """

        results = await self.search_all(
            org_id=org_id,
            query=query,
            document_limit=document_limit,
            vendor_limit=vendor_limit,
            organization_limit=organization_limit,
        )

        return self.build_context(
            documents=results["documents"],
            vendors=results["vendors"],
            organization=results["organization"],
        )

    # =========================================================
    # Similarity Filtering
    # =========================================================

    @staticmethod
    def filter_results(
        results: list[dict],
        *,
        minimum_similarity: float = 0.70,
    ) -> list[dict]:
        """
        Remove low-confidence semantic matches.
        """

        filtered = []

        for result in results:

            similarity = (
                result.get("similarity")
                or result.get("score")
                or 0.0
            )

            if similarity >= minimum_similarity:
                filtered.append(result)

        return filtered

    # =========================================================
    # Result Deduplication
    # =========================================================

    @staticmethod
    def deduplicate_results(
        results: list[dict],
        key: str,
    ) -> list[dict]:
        """
        Remove duplicate semantic matches while preserving
        ranking order.
        """

        seen = set()

        unique = []

        for result in results:

            value = result.get(key)

            if value in seen:
                continue

            seen.add(value)

            unique.append(result)

        return unique

        # =========================================================
    # Context Budgeting
    # =========================================================

    @staticmethod
    def trim_context(
        context: str,
        *,
        max_characters: int = 12000,
    ) -> str:
        """
        Trim context before sending to the LLM.

        Keeps the beginning of the context, which contains
        the highest-ranked semantic matches.
        """

        if len(context) <= max_characters:
            return context

        return (
            context[:max_characters].rstrip()
            + "\n\n[Context truncated]"
        )

    # =========================================================
    # Ranked Context Retrieval
    # =========================================================

    async def retrieve_ranked_context(
        self,
        *,
        org_id: UUID,
        query: str,
        minimum_similarity: float = 0.70,
        document_limit: int = 8,
        vendor_limit: int = 5,
        organization_limit: int = 1,
        max_characters: int = 12000,
    ) -> str:
        """
        Retrieve, clean and prepare semantic context
        for AI generation.
        """

        query_embedding = await self.embedding_service.create_embedding(
            query,
        )

        documents = await self.embedding_repository.search_document_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=document_limit,
        )

        vendors = await self.embedding_repository.search_vendor_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=vendor_limit,
        )

        organization = await self.embedding_repository.search_organization_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=organization_limit,
        )

        documents = self.filter_results(
            documents,
            minimum_similarity=minimum_similarity,
        )

        vendors = self.filter_results(
            vendors,
            minimum_similarity=minimum_similarity,
        )

        organization = self.filter_results(
            organization,
            minimum_similarity=minimum_similarity,
        )

        documents = self.deduplicate_results(
            documents,
            "document_id",
        )

        vendors = self.deduplicate_results(
            vendors,
            "vendor_id",
        )

        organization = self.deduplicate_results(
            organization,
            "org_id",
        )

        context = self.build_context(
            documents=documents,
            vendors=vendors,
            organization=organization,
        )

        return self.trim_context(
            context,
            max_characters=max_characters,
        )

    # =========================================================
    # Metadata Filters
    # =========================================================

    @staticmethod
    def filter_document_metadata(
        results: list[dict],
        *,
        vendor_id: UUID | None = None,
        currency: str | None = None,
        document_type: str | None = None,
    ) -> list[dict]:
        """
        Apply metadata filtering after semantic retrieval.
        """

        filtered: list[dict] = []

        for result in results:

            if (
                vendor_id
                and str(result.get("vendor_id")) != str(vendor_id)
            ):
                continue

            if (
                currency
                and result.get("currency") != currency
            ):
                continue

            if (
                document_type
                and result.get("document_type") != document_type
            ):
                continue

            filtered.append(result)

        return filtered

    # =========================================================
    # Sorting
    # =========================================================

    @staticmethod
    def sort_results(
        results: list[dict],
    ) -> list[dict]:
        """
        Highest similarity first.
        """

        return sorted(
            results,
            key=lambda item: (
                item.get("similarity")
                or item.get("score")
                or 0.0
            ),
            reverse=True,
        )

    # =========================================================
    # Top Results
    # =========================================================

    @staticmethod
    def top_results(
        results: list[dict],
        *,
        limit: int,
    ) -> list[dict]:
        """
        Return only the highest-ranked matches.
        """

        return results[:limit]

    # =========================================================
    # Search Statistics
    # =========================================================

    @staticmethod
    def statistics(
        *,
        documents: list[dict],
        vendors: list[dict],
        organization: list[dict],
    ) -> dict:
        """
        Retrieval metrics useful for logging.
        """

        return {
            "documents_found": len(documents),
            "vendors_found": len(vendors),
            "organization_found": len(organization),
            "total_results": (
                len(documents)
                + len(vendors)
                + len(organization)
            ),
        }

        # =========================================================
    # Public Retrieval API
    # =========================================================

    async def retrieve(
        self,
        *,
        org_id: UUID,
        query: str,
        minimum_similarity: float = 0.70,
        document_limit: int = 8,
        vendor_limit: int = 5,
        organization_limit: int = 1,
        max_characters: int = 12000,
    ) -> dict:
        """
        Complete semantic retrieval pipeline.

        Returns prompt-ready context together with the
        ranked semantic matches.
        """

        query_embedding = await self.embedding_service.create_embedding(
            query,
        )

        documents = await self.embedding_repository.search_document_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=document_limit,
        )

        vendors = await self.embedding_repository.search_vendor_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=vendor_limit,
        )

        organization = await self.embedding_repository.search_organization_context(
            org_id=org_id,
            embedding=query_embedding,
            limit=organization_limit,
        )

        documents = self.filter_results(
            documents,
            minimum_similarity=minimum_similarity,
        )

        vendors = self.filter_results(
            vendors,
            minimum_similarity=minimum_similarity,
        )

        organization = self.filter_results(
            organization,
            minimum_similarity=minimum_similarity,
        )

        documents = self.sort_results(documents)
        vendors = self.sort_results(vendors)
        organization = self.sort_results(organization)

        documents = self.top_results(
            documents,
            limit=document_limit,
        )

        vendors = self.top_results(
            vendors,
            limit=vendor_limit,
        )

        organization = self.top_results(
            organization,
            limit=organization_limit,
        )

        context = self.build_context(
            documents=documents,
            vendors=vendors,
            organization=organization,
        )

        context = self.trim_context(
            context,
            max_characters=max_characters,
        )

        return {
            "query": query,
            "context": context,
            "documents": documents,
            "vendors": vendors,
            "organization": organization,
            "statistics": self.statistics(
                documents=documents,
                vendors=vendors,
                organization=organization,
            ),
        }