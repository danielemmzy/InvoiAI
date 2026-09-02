"""
============================================================
Analysis Domain Model

Mirror of PostgreSQL document_analyses table.

Rules
-----
- One field per database column
- No business logic
- No validation logic
- No request/response schemas
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import (
    FraudSignal,
    RecommendationType,
    RiskLevel,
)
from app.models.domain.base import DomainModel


class Analysis(DomainModel):
    """
    Mirrors the document_analyses table.
    """

    # ==========================================================
    # Identity
    # ==========================================================

    id: UUID

    document_id: UUID

    org_id: UUID

    # ==========================================================
    # Overall AI Decision
    # ==========================================================

    health_score: int

    risk_level: RiskLevel

    recommendation: RecommendationType

    summary: str

    # ==========================================================
    # Scores
    # ==========================================================

    overall_score: int

    financial_score: int

    fraud_score: int

    duplicate_score: int

    vendor_score: int

    policy_score: int

    confidence_score: int

    # ==========================================================
    # AI Outputs
    # ==========================================================

    reasons: dict[str, Any] = Field(default_factory=dict)

    positive_signals: dict[str, Any] = Field(default_factory=dict)

    action_items: dict[str, Any] = Field(default_factory=dict)

    module_results: dict[str, Any] = Field(default_factory=dict)

    # ==========================================================
    # OCR Validation
    # ==========================================================

    ocr_confidence: int

    # ==========================================================
    # Math Validation
    # ==========================================================

    math_passed: bool

    math_expected_total: Decimal

    math_actual_total: Decimal

    math_variance: Decimal

    # ==========================================================
    # Vendor Intelligence
    # ==========================================================

    vendor_known: bool

    vendor_risk_score: int

    # ==========================================================
    # Duplicate Detection
    # ==========================================================

    is_duplicate: bool

    duplicate_of: UUID | None = None

    duplicate_similarity: Decimal | None = None

    # ==========================================================
    # Amount Intelligence
    # ==========================================================

    amount_anomaly: bool

    amount_vs_avg_pct: Decimal | None = None

    std_deviations_from_avg: Decimal | None = None

    # ==========================================================
    # Purchase Order Matching
    # ==========================================================

    po_matched: bool

    po_id: UUID | None = None

    # ==========================================================
    # Fraud Detection
    # ==========================================================

    fraud_signals: list[FraudSignal] = Field(default_factory=list)

    # ==========================================================
    # Compliance
    # ==========================================================

    compliance_passed: bool

    # ==========================================================
    # Human Review
    # ==========================================================

    reviewed_by: UUID | None = None

    reviewed_at: datetime | None = None

    final_decision: RecommendationType | None = None

    override_reason: str | None = None

    # ==========================================================
    # AI Metadata
    # ==========================================================

    model: str

    engine_version: str

    analysis_version: str

    prompt_version: str

    temperature: Decimal

    processing_ms: int

    tokens_used: int

    tokens_cost_usd: Decimal

    # ==========================================================
    # Audit
    # ==========================================================

    created_at: datetime

    updated_at: datetime