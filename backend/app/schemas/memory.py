"""
============================================================
Memory Schemas

API request/response models.
============================================================
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ============================================================
# Document Memory Response
# ============================================================

class DocumentMemoryResponse(BaseModel):
    """
    Document memory returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    document_id: UUID

    org_id: UUID

    memory_key: str

    memory_value: str

    confidence_score: float

    created_at: datetime

    updated_at: datetime


# ============================================================
# Vendor Memory Response
# ============================================================

class VendorMemoryResponse(BaseModel):
    """
    Vendor memory returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    vendor_id: UUID

    org_id: UUID

    memory_key: str

    memory_value: str

    confidence_score: float

    created_at: datetime

    updated_at: datetime


# ============================================================
# Organization Memory Response
# ============================================================

class OrganizationMemoryResponse(BaseModel):
    """
    Organization memory returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    memory_key: str

    memory_value: str

    confidence_score: float

    created_at: datetime

    updated_at: datetime