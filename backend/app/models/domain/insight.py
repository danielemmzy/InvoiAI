"""
============================================================
Insight Domain Model

Mirrors the `insights` table from Flow 10.
============================================================
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.insight import InsightSeverity, InsightType
from app.models.domain.base import TimestampedEntity


class Insight(TimestampedEntity):
    org_id: UUID

    insight_type: InsightType
    severity: InsightSeverity

    title: str
    description: str
    data: dict[str, Any] = Field(default_factory=dict)

    affected_resource_type: str | None = None
    affected_resource_id: UUID | None = None

    recommended_action: str | None = None

    is_read: bool = False
    is_dismissed: bool = False

    expires_at: datetime | None = None
