"""
============================================================
Payment Allocation Domain Model

A payment may be allocated to multiple documents.

ERP style.

============================================================
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.domain.base import TimestampedEntity


JsonDict = dict[str, Any]


class PaymentAllocation(TimestampedEntity):

    org_id: UUID

    payment_id: UUID

    document_id: UUID

    allocated_amount: Decimal

    metadata: JsonDict = Field(
        default_factory=dict,
    )