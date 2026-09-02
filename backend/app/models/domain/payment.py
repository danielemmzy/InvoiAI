"""
============================================================
Payment Domain Model

Mirrors PostgreSQL payments table.

Imported from accounting providers
such as:

• QuickBooks
• Xero
• Sage

============================================================
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import IntegrationProvider
from app.models.domain.base import TimestampedEntity

JsonDict = dict[str, Any]


class Payment(TimestampedEntity):
    """
    Mirrors payments table.
    """

    org_id: UUID

    vendor_id: UUID | None = None

    document_id: UUID | None = None

    payment_number: str | None = None

    external_id: str | None = None

    provider: IntegrationProvider | None = None

    payment_method: str | None = None

    amount: float

    currency: str = "USD"

    payment_date: date | None = None

    status: str | None = None

    reference: str | None = None

    synced_at: datetime | None = None

    last_modified_external: datetime | None = None

    metadata: JsonDict = Field(default_factory=dict)