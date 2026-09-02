"""
============================================================
Vendor Schemas

API request/response models.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import RiskLevel


# ============================================================
# Create
# ============================================================

class VendorCreate(BaseModel):

    name: str

    email: str | None = None

    phone: str | None = None

    website: str | None = None

    address_line1: str | None = None

    address_line2: str | None = None

    city: str | None = None

    state: str | None = None

    postal_code: str | None = None

    country: str | None = None

    tax_id: str | None = None

    registration_number: str | None = None

    industry: str | None = None

    category: str | None = None


# ============================================================
# Update
# ============================================================

class VendorUpdate(BaseModel):

    name: str | None = None

    aliases: list[str] | None = None

    email: str | None = None

    phone: str | None = None

    website: str | None = None

    address_line1: str | None = None

    address_line2: str | None = None

    city: str | None = None

    state: str | None = None

    postal_code: str | None = None

    country: str | None = None

    tax_id: str | None = None

    registration_number: str | None = None

    industry: str | None = None

    category: str | None = None

    is_verified: bool | None = None

    is_preferred: bool | None = None

    is_blocked: bool | None = None

    blocked_reason: str | None = None

    notes: str | None = None

    tags: list[str] | None = None


# ============================================================
# Response
# ============================================================

class VendorResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    name: str

    normalized_name: str

    aliases: list[str]

    email: str | None

    phone: str | None

    website: str | None

    address_line1: str | None

    address_line2: str | None

    city: str | None

    state: str | None

    postal_code: str | None

    country: str | None

    tax_id: str | None

    registration_number: str | None

    industry: str | None

    category: str | None

    bank_name: str | None

    bank_country: str | None

    invoice_count: int

    receipt_count: int

    credit_note_count: int

    po_count: int

    total_document_count: int

    total_spend: Decimal

    average_spend: Decimal

    median_spend: Decimal

    largest_amount: Decimal

    smallest_amount: Decimal

    stddev_spend: Decimal

    price_volatility: Decimal

    first_seen: datetime | None

    last_seen: datetime | None

    average_payment_days: int | None

    typical_invoice_weekday: int | None

    typical_invoice_month: int | None

    typical_currency: str | None

    currencies_used: list[str]

    duplicate_count: int

    fraud_flags: int

    anomaly_count: int

    rejection_count: int

    monthly_spend_trend: dict[str, Any]

    spend_category_breakdown: dict[str, Any]

    risk_score: int

    risk_level: RiskLevel

    is_verified: bool

    is_preferred: bool

    is_blocked: bool

    blocked_reason: str | None

    blocked_at: datetime | None

    blocked_by: UUID | None

    verified_at: datetime | None

    verified_by: UUID | None

    ai_summary: str | None

    ai_risk_explanation: str | None

    ai_last_updated_at: datetime | None

    ai_model_used: str | None

    external_ids: dict[str, Any]

    tags: list[str]

    notes: str | None

    metadata: dict[str, Any]

    created_at: datetime

    updated_at: datetime


# ============================================================
# Search
# ============================================================

class VendorSearchResponse(BaseModel):

    items: list[VendorResponse] = Field(default_factory=list)

    total: int