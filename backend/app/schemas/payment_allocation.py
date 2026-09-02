from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


JsonDict = dict[str, Any]


class PaymentAllocationResponse(BaseModel):

    id: UUID

    org_id: UUID

    payment_id: UUID

    document_id: UUID

    allocated_amount: Decimal

    metadata: JsonDict = Field(default_factory=dict)

    created_at: datetime

    updated_at: datetime