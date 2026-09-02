"""
============================================================
Analysis Context

Runtime AI analysis context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel

from app.core.enum.database import RecommendationType, RiskLevel


class AnalysisContext(BaseModel):
    """
    Current document analysis.
    """

    analysis_id: UUID

    document_id: UUID

    org_id: UUID

    health_score: int | None = None

    overall_score: int | None = None

    risk_level: RiskLevel | None = None

    recommendation: RecommendationType | None = None

    ai_model: str | None = None

    prompt_version: str | None = None

    processing_ms: int = 0