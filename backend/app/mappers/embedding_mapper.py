"""
============================================================
Embedding Mapper
============================================================
"""

from __future__ import annotations

import json

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

    @classmethod
    def to_domain(
        cls,
        row: dict | None,
    ) -> DocumentEmbedding | None:
        """
        Convert Supabase/PostgreSQL row into DocumentEmbedding.

        PostgreSQL/pgvector may return the embedding column as a
        string such as:

            "[-0.023330688,-0.0219879,...]"

        The domain model requires:

            list[float]
        """

        if row is None:
            return None

        payload = dict(row)

        embedding = payload.get("embedding")

        if isinstance(embedding, str):
            try:
                payload["embedding"] = json.loads(embedding)
            except (json.JSONDecodeError, TypeError):
                cleaned = embedding.strip()

                if cleaned.startswith("[") and cleaned.endswith("]"):
                    cleaned = cleaned[1:-1]

                if cleaned.strip():
                    payload["embedding"] = [
                        float(value.strip())
                        for value in cleaned.split(",")
                        if value.strip()
                    ]
                else:
                    payload["embedding"] = []

        return cls.domain_model.model_validate(payload)

    @staticmethod
    def to_insert(
        embedding: DocumentEmbedding | dict,
    ):

        if isinstance(embedding, dict):
            payload = dict(embedding)

            for key in ("id", "document_id", "org_id"):
                if key in payload and payload[key] is not None:
                    payload[key] = str(payload[key])

            return payload

        return {
            "document_id": str(embedding.document_id),
            "org_id": str(embedding.org_id),
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

    @classmethod
    def to_domain(
        cls,
        row: dict | None,
    ) -> VendorEmbedding | None:

        if row is None:
            return None

        payload = dict(row)

        embedding = payload.get("embedding")

        if isinstance(embedding, str):
            try:
                payload["embedding"] = json.loads(embedding)
            except (json.JSONDecodeError, TypeError):
                cleaned = embedding.strip()

                if cleaned.startswith("[") and cleaned.endswith("]"):
                    cleaned = cleaned[1:-1]

                payload["embedding"] = [
                    float(value.strip())
                    for value in cleaned.split(",")
                    if value.strip()
                ]

        return cls.domain_model.model_validate(payload)

    @staticmethod
    def to_insert(
        embedding: VendorEmbedding | dict,
    ):

        if isinstance(embedding, dict):
            payload = dict(embedding)

            for key in ("id", "vendor_id", "org_id"):
                if key in payload and payload[key] is not None:
                    payload[key] = str(payload[key])

            return payload

        return {
            "vendor_id": str(embedding.vendor_id),
            "org_id": str(embedding.org_id),
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

    @classmethod
    def to_domain(
        cls,
        row: dict | None,
    ) -> OrganizationEmbedding | None:

        if row is None:
            return None

        payload = dict(row)

        embedding = payload.get("embedding")

        if isinstance(embedding, str):
            try:
                payload["embedding"] = json.loads(embedding)
            except (json.JSONDecodeError, TypeError):
                cleaned = embedding.strip()

                if cleaned.startswith("[") and cleaned.endswith("]"):
                    cleaned = cleaned[1:-1]

                payload["embedding"] = [
                    float(value.strip())
                    for value in cleaned.split(",")
                    if value.strip()
                ]

        return cls.domain_model.model_validate(payload)

    @staticmethod
    def to_insert(
        embedding: OrganizationEmbedding | dict,
    ):

        if isinstance(embedding, dict):
            payload = dict(embedding)

            for key in ("id", "org_id"):
                if key in payload and payload[key] is not None:
                    payload[key] = str(payload[key])

            return payload

        return {
            "org_id": str(embedding.org_id),
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
