"""
============================================================
Insight Schemas
============================================================
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enum.insight import InsightSeverity, InsightType


class InsightResponse(BaseModel):
    id: UUID
    insight_type: InsightType
    severity: InsightSeverity
    title: str
    description: str
    data: dict[str, Any] = Field(default_factory=dict)
    affected_resource_type: str | None = None
    affected_resource_id: UUID | None = None
    recommended_action: str | None = None
    is_read: bool
    is_dismissed: bool
    expires_at: datetime | None = None
    created_at: datetime


class InsightDismissRequest(BaseModel):
    is_dismissed: bool = True
