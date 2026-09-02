"""
============================================================
Embedding Domain Models

Mirror PostgreSQL embedding tables.

Tables
------
- document_embeddings
- vendor_embeddings
- organization_embeddings

Notes
-----
These tables share an identical structure except for the
foreign-key column, so a common base model is used.
============================================================
"""

from datetime import datetime
from uuid import UUID

from app.models.domain.base import DomainModel


# ============================================================
# Shared Base
# ============================================================

class BaseEmbedding(DomainModel):
    """
    Shared fields for all embedding tables.
    """

    id: UUID

    org_id: UUID

    embedding: list[float]

    source_text: str

    model_used: str

    created_at: datetime

    updated_at: datetime


# ============================================================
# Document Embeddings
# ============================================================

class DocumentEmbedding(BaseEmbedding):
    """
    Mirrors document_embeddings.
    """

    document_id: UUID


# ============================================================
# Vendor Embeddings
# ============================================================

class VendorEmbedding(BaseEmbedding):
    """
    Mirrors vendor_embeddings.
    """

    vendor_id: UUID


# ============================================================
# Organization Embeddings
# ============================================================

class OrganizationEmbedding(BaseEmbedding):
    """
    Mirrors organization_embeddings.
    """

    org_id: UUID

