"""
============================================================
Embedding Mapper
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.embedding import (
    DocumentEmbedding,
    OrganizationEmbedding,
    VendorEmbedding,
)

from app.schemas.embedding import (
    DocumentEmbeddingResponse,
    OrganizationEmbeddingResponse,
    VendorEmbeddingResponse,
)


class DocumentEmbeddingMapper(
    BaseMapper[
        DocumentEmbedding,
        DocumentEmbeddingResponse,
    ]
):
    domain_model = DocumentEmbedding
    response_model = DocumentEmbeddingResponse

    @staticmethod
    def to_insert(
        embedding: DocumentEmbedding | dict,
    ):

        if isinstance(embedding, dict):
            return embedding

        return {
            "document_id": embedding.document_id,
            "org_id": embedding.org_id,
            "embedding": embedding.embedding,
            "source_text": embedding.source_text,
            "model_used": embedding.model_used,
        }

    @staticmethod
    def to_update(
        embedding: DocumentEmbedding | dict,
    ):

        return DocumentEmbeddingMapper.to_insert(
            embedding,
        )


class VendorEmbeddingMapper(
    BaseMapper[
        VendorEmbedding,
        VendorEmbeddingResponse,
    ]
):
    domain_model = VendorEmbedding
    response_model = VendorEmbeddingResponse

    @staticmethod
    def to_insert(
        embedding: VendorEmbedding | dict,
    ):

        if isinstance(embedding, dict):
            return embedding

        return {
            "vendor_id": embedding.vendor_id,
            "org_id": embedding.org_id,
            "embedding": embedding.embedding,
            "source_text": embedding.source_text,
            "model_used": embedding.model_used,
        }

    @staticmethod
    def to_update(
        embedding: VendorEmbedding | dict,
    ):

        return VendorEmbeddingMapper.to_insert(
            embedding,
        )


class OrganizationEmbeddingMapper(
    BaseMapper[
        OrganizationEmbedding,
        OrganizationEmbeddingResponse,
    ]
):
    domain_model = OrganizationEmbedding
    response_model = OrganizationEmbeddingResponse

    @staticmethod
    def to_insert(
        embedding: OrganizationEmbedding | dict,
    ):

        if isinstance(embedding, dict):
            return embedding

        return {
            "org_id": embedding.org_id,
            "embedding": embedding.embedding,
            "source_text": embedding.source_text,
            "model_used": embedding.model_used,
        }

    @staticmethod
    def to_update(
        embedding: OrganizationEmbedding | dict,
    ):

        return OrganizationEmbeddingMapper.to_insert(
            embedding,
        )