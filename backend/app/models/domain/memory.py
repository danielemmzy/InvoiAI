"""
============================================================
Memory Domain Models

Mirror PostgreSQL tables.

- document_memory
- organization_memory
- vendor_memory

Repositories return these models only.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.domain.base import DomainModel


JsonDict = dict[str, Any]


# ============================================================
# Document Memory
# ============================================================

class DocumentMemory(DomainModel):
    """
    Mirrors document_memory table.
    """

    id: UUID

    document_id: UUID

    org_id: UUID

    summary: str

    key_facts: JsonDict = Field(default_factory=dict)

    anomalies: JsonDict = Field(default_factory=dict)

    context_notes: str | None = None

    embedding: Any | None = None

    model_used: str

    prompt_version: str

    created_at: datetime

    updated_at: datetime


# ============================================================
# Organization Memory
# ============================================================

class OrganizationMemory(DomainModel):
    """
    Mirrors organization_memory table.
    """

    id: UUID

    org_id: UUID

    financial_summary: str

    spending_patterns: JsonDict = Field(default_factory=dict)

    top_vendors_summary: JsonDict = Field(default_factory=dict)

    risk_posture_summary: str

    anomaly_history_summary: str

    total_documents_processed: int

    total_spend_processed: Decimal

    avg_document_amount: Decimal

    avg_health_score: Decimal

    documents_auto_approved: int

    documents_flagged: int

    documents_rejected: int

    total_duplicates_caught: int

    total_fraud_prevented: Decimal

    embedding: Any | None = None

    model_used: str

    prompt_version: str

    last_updated_at: datetime

    update_count: int

    created_at: datetime

    updated_at: datetime


# ============================================================
# Vendor Memory
# ============================================================

class VendorMemory(DomainModel):
    """
    Mirrors vendor_memory table.
    """

    id: UUID

    vendor_id: UUID

    org_id: UUID

    payment_behaviour: str

    seasonal_patterns: str

    price_trend: str

    risk_narrative: str

    relationship_summary: str

    invoice_patterns: JsonDict = Field(default_factory=dict)

    price_trend_data: JsonDict = Field(default_factory=dict)

    anomaly_log: JsonDict = Field(default_factory=dict)

    fraud_incident_log: JsonDict = Field(default_factory=dict)

    model_used: str

    engine_version: str

    prompt_version: str

    last_updated_at: datetime

    update_count: int

    created_at: datetime