"""
============================================================
Base Domain Models

Every database entity inherits from these models.

These models mirror PostgreSQL tables.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid",
    )


class Entity(DomainModel):
    id: UUID


class TimestampedEntity(Entity):
    created_at: datetime
    updated_at: datetime


class Money(DomainModel):
    currency: str
    total_amount: Decimal