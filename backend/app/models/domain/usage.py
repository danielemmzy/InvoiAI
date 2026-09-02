"""
============================================================
Usage Domain Model

Mirrors PostgreSQL table.

- usage
============================================================
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.domain.base import DomainModel


class Usage(DomainModel):
    """
    Mirrors usage table.
    """

    org_id: UUID

    month: str

    document_count: int

    api_calls: int

    storage_bytes: int

    ai_tokens_used: int

    ai_cost_usd: Decimal

    last_document_at: datetime | None = None

    last_document_by: UUID | None = None

    last_ai_request_at: datetime | None = None

    last_ai_request_by: UUID | None = None

    last_api_request_at: datetime | None = None

    last_api_request_by: UUID | None = None

    last_updated_at: datetime