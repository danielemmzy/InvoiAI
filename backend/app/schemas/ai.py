from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

"""
============================================================
AI Schemas

API response models.

- ai_events
- ai_score_explanations
============================================================
"""


# ============================================================
# AI Event Response
# ============================================================

class AIEventResponse(BaseModel):
    """
    AI event returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    event_type: str

    resource_type: str

    resource_id: UUID | None

    payload: dict[str, Any]

    model: str

    engine_version: str

    prompt_version: str

    tokens_used: int

    processing_ms: int

    request_id: str | None

    job_id: UUID | None

    created_at: datetime


# ============================================================
# AI Score Explanation Response
# ============================================================

class AIScoreExplanationResponse(BaseModel):
    """
    AI explanation for a scoring module.
    """

    model_config = ConfigDict(from_attributes=True)

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

    temperature: Decimal | None

    tokens_used: int

    created_at: datetime


# ============================================================
# Lists
# ============================================================

class AIEventListResponse(BaseModel):

    items: list[AIEventResponse] = Field(default_factory=list)

    total: int


class AIScoreExplanationListResponse(BaseModel):

    items: list[AIScoreExplanationResponse] = Field(default_factory=list)

    total: int