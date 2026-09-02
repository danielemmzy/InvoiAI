"""
============================================================
Vendor Domain Model

Mirrors the vendors table.

Repositories return this model.

No API request/response models belong here.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import RiskLevel
from app.models.domain.base import TimestampedEntity


JsonDict = dict[str, Any]


class Vendor(TimestampedEntity):
    """
    Mirrors the vendors table.
    """

    org_id: UUID

    # ---------------------------------------------------------
    # Identity
    # ---------------------------------------------------------

    name: str

    normalized_name: str

    aliases: list[str] = Field(default_factory=list)

    # ---------------------------------------------------------
    # Contact
    # ---------------------------------------------------------

    email: str | None = None

    phone: str | None = None

    website: str | None = None

    # ---------------------------------------------------------
    # Address
    # ---------------------------------------------------------

    address_line1: str | None = None

    address_line2: str | None = None

    city: str | None = None

    state: str | None = None

    postal_code: str | None = None

    country: str | None = None

    # ---------------------------------------------------------
    # Business
    # ---------------------------------------------------------

    tax_id: str | None = None

    registration_number: str | None = None

    industry: str | None = None

    category: str | None = None

    # ---------------------------------------------------------
    # Banking
    # ---------------------------------------------------------

    bank_account_hash: str | None = None

    bank_name: str |None = None

    bank_country: str | None = None

    bank_account_changed_at: datetime | None = None

    bank_change_count: int

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

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

    first_seen: datetime | None = None

    last_seen: datetime | None = None

    average_payment_days: int | None = None

    typical_invoice_weekday: int | None = None

    typical_invoice_month: int | None = None

    typical_currency: str | None = None

    currencies_used: list[str] = Field(default_factory=list)

    # ---------------------------------------------------------
    # Risk
    # ---------------------------------------------------------

    duplicate_count: int

    fraud_flags: int

    anomaly_count: int

    rejection_count: int

    monthly_spend_trend: JsonDict = Field(default_factory=dict)

    spend_category_breakdown: JsonDict = Field(default_factory=dict)

    risk_score: int

    risk_level: RiskLevel

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    is_verified: bool

    is_preferred: bool

    is_blocked: bool

    blocked_reason: str | None = None

    blocked_at: datetime | None = None

    blocked_by: UUID | None = None

    verified_at: datetime | None = None

    verified_by: UUID | None = None

    # ---------------------------------------------------------
    # AI
    # ---------------------------------------------------------

    ai_summary: str | None = None

    ai_risk_explanation: str | None = None

    ai_last_updated_at: datetime | None = None

    ai_model_used: str | None = None

    # ---------------------------------------------------------
    # Misc
    # ---------------------------------------------------------

    external_ids: JsonDict = Field(default_factory=dict)

    tags: list[str] = Field(default_factory=list)

    notes: str | None = None

    metadata: JsonDict = Field(default_factory=dict)