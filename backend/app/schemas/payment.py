"""
============================================================
Payment Response Schema

Returned by Finance API.

Mirrors Payment domain model.

============================================================
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enum.database import IntegrationProvider


JsonDict = dict[str, Any]


class PaymentResponse(BaseModel):
    """
    Payment response schema.
    """

    id: UUID

    org_id: UUID

    vendor_id: UUID | None = None

    payment_number: str

    external_id: str | None = None

    provider: IntegrationProvider | None = None

    payment_method: str | None = None

    amount: Decimal

    currency: str

    payment_date: date

    status: str

    reference: str | None = None

    synced_at: datetime | None = None

    last_modified_external: datetime | None = None

    metadata: JsonDict = Field(
        default_factory=dict,
    )

    created_at: datetime

    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }