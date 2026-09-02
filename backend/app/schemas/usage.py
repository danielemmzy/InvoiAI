from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


"""
============================================================
Usage Schemas

API response models.
============================================================
"""


# ============================================================
# Usage Response
# ============================================================

class UsageResponse(BaseModel):
    """
    Organization monthly usage.
    """

    model_config = ConfigDict(from_attributes=True)

    org_id: UUID

    month: str

    document_count: int

    api_calls: int

    storage_bytes: int

    ai_tokens_used: int

    ai_cost_usd: Decimal

    last_document_at: datetime | None

    last_document_by: UUID | None

    last_ai_request_at: datetime | None

    last_ai_request_by: UUID | None

    last_api_request_at: datetime | None

    last_api_request_by: UUID | None

    last_updated_at: datetime