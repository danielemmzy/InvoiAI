"""
============================================================
Analysis Schemas

API request/response models.

These models DO NOT mirror the database directly.
They define the public API contract.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import RecommendationType, RiskLevel


# ============================================================
# Create
# ============================================================

class AnalysisCreate(BaseModel):
    """
    Create analysis.
    """

    document_id: UUID


# ============================================================
# Update
# ============================================================

class AnalysisUpdate(BaseModel):
    """
    Partial analysis update.
    """

    health_score: int | None = None

    risk_level: RiskLevel | None = None

    recommendation: RecommendationType | None = None

    summary: str | None = None

    overall_score: int | None = None

    financial_score: int | None = None

    fraud_score: int | None = None

    duplicate_score: int | None = None

    vendor_score: int | None = None

    policy_score: int | None = None

    confidence_score: int | None = None

    reasons: dict[str, Any] | None = None

    positive_signals: dict[str, Any] | None = None

    action_items: dict[str, Any] | None = None

    module_results: dict[str, Any] | None = None

    reviewed_by: UUID | None = None

    final_decision: RecommendationType | None = None

    override_reason: str | None = None


# ============================================================
# Response
# ============================================================

class AnalysisResponse(BaseModel):
    """
    Analysis returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    document_id: UUID

    org_id: UUID

    health_score: int

    risk_level: RiskLevel

    recommendation: RecommendationType

    summary: str

    overall_score: int

    financial_score: int

    fraud_score: int

    duplicate_score: int

    vendor_score: int

    policy_score: int

    confidence_score: int

    reasons: dict[str, Any]

    positive_signals: dict[str, Any]

    action_items: dict[str, Any]

    module_results: dict[str, Any]

    ocr_confidence: int

    math_passed: bool

    math_expected_total: Decimal | None

    math_actual_total: Decimal | None

    math_variance: Decimal | None

    vendor_known: bool

    vendor_risk_score: int

    is_duplicate: bool

    duplicate_of: UUID | None

    duplicate_similarity: Decimal | None

    amount_anomaly: bool

    amount_vs_avg_pct: Decimal | None

    std_deviations_from_avg: Decimal | None

    po_matched: bool

    po_id: UUID | None

    fraud_signals: list[str]

    compliance_passed: bool

    reviewed_by: UUID | None

    reviewed_at: datetime | None

    final_decision: RecommendationType | None

    override_reason: str | None

    model: str | None

    engine_version: str | None

    analysis_version: str | None

    prompt_version: str | None

    temperature: Decimal | None

    processing_ms: int | None

    tokens_used: int | None

    tokens_cost_usd: Decimal | None

    created_at: datetime

    updated_at: datetime


# ============================================================
# List Response
# ============================================================

class AnalysisListResponse(BaseModel):
    """
    List of analyses.
    """

    items: list[AnalysisResponse] = Field(default_factory=list)

    total: int