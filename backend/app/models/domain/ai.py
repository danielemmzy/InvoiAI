"""
============================================================
AI Domain Models

Mirror PostgreSQL AI tables.

No business logic.
No API schemas.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.domain.base import DomainModel


class AIEvent(DomainModel):
    id: UUID
    org_id: UUID

    event_type: str
    resource_type: str
    resource_id: UUID

    payload: dict[str, Any]

    model: str
    engine_version: str
    prompt_version: str

    tokens_used: int
    processing_ms: int

    request_id: str
    job_id: UUID

    created_at: datetime


class AIScoreExplanation(DomainModel):
    id: UUID

    analysis_id: UUID
    org_id: UUID

    module_name: str

    reasoning: str

    evidence: dict[str, Any]

    citations: dict[str, Any]

    affected_fields: list[str]

    confidence_explanation: str

    score: int

    score_breakdown: dict[str, Any]

    threshold_used: dict[str, Any]

    prompt_used: str

    model: str
    prompt_version: str

    temperature: Decimal

    tokens_used: int

    created_at: datetime