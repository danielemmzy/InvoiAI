"""
============================================================
Embedding Schemas

API request/response models.
============================================================
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ============================================================
# Document Embedding Response
# ============================================================

class DocumentEmbeddingResponse(BaseModel):
    """
    Document embedding returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    document_id: UUID

    org_id: UUID

    chunk_index: int

    chunk_text: str

    embedding_model: str

    vector_dimensions: int

    created_at: datetime

    updated_at: datetime


# ============================================================
# Vendor Embedding Response
# ============================================================

class VendorEmbeddingResponse(BaseModel):
    """
    Vendor embedding returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    vendor_id: UUID

    org_id: UUID

    embedding_model: str

    vector_dimensions: int

    created_at: datetime

    updated_at: datetime


# ============================================================
# Organization Embedding Response
# ============================================================

class OrganizationEmbeddingResponse(BaseModel):
    """
    Organization embedding returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    embedding_model: str

    vector_dimensions: int

    created_at: datetime

    updated_at: datetime

class DocumentEmbeddingMatch(BaseModel):
    document_id: UUID
    similarity: float
    source_text: str

# ============================================================
# Semantic Search Results
# ============================================================

class DocumentEmbeddingMatch(BaseModel):

    document_id: UUID

    org_id: UUID

    similarity: float

    source_text: str


class VendorEmbeddingMatch(BaseModel):

    vendor_id: UUID

    org_id: UUID

    similarity: float

    source_text: str


class OrganizationEmbeddingMatch(BaseModel):

    org_id: UUID

    similarity: float

    source_text: str