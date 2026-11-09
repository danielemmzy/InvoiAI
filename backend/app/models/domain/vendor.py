"""
============================================================
Vendor Domain Model

Mirrors the vendors table.

Repositories return this model.

No API request/response models belong here.
============================================================
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import RiskLevel
from app.core.enum.database import IntegrationProvider
from app.models.domain.base import TimestampedEntity


JsonDict = dict[str, Any]


class Vendor(TimestampedEntity):
    """
    Mirrors the vendors table.
    """

    org_id: UUID

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    provider: IntegrationProvider | None = None

    external_id: str | None = None

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

    bank_change_count: int = 0

    bank_change_pending: bool = False

    bank_change_requested_at: datetime | None = None

    bank_change_verified_at: datetime | None = None

    # ---------------------------------------------------------
    # AP policy
    # ---------------------------------------------------------

    po_required: bool = False

    receipt_required: bool = False

    approval_threshold: Decimal | None = None

    default_gl_account_id: UUID | None = None

    default_department_id: UUID | None = None

    default_cost_center_id: UUID | None = None

    requires_w9: bool = False

    w9_on_file: bool = False

    w9_document_url: str | None = None

    payment_hold: bool = False

    payment_hold_reason: str | None = None

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    invoice_count: int = 0

    receipt_count: int = 0

    credit_note_count: int = 0

    po_count: int = 0

    total_document_count: int = 0

    total_spend: Decimal = Decimal("0")

    average_spend: Decimal = Decimal("0")

    median_spend: Decimal = Decimal("0")

    largest_amount: Decimal = Decimal("0")

    smallest_amount: Decimal = Decimal("0")

    stddev_spend: Decimal = Decimal("0")

    price_volatility: Decimal = Decimal("0")

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

    duplicate_count: int = 0

    fraud_flags: int = 0

    anomaly_count: int = 0

    rejection_count: int = 0

    monthly_spend_trend: JsonDict = Field(default_factory=dict)

    spend_category_breakdown: JsonDict = Field(default_factory=dict)

    risk_score: int = 0

    risk_level: RiskLevel = RiskLevel.LOW

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    is_verified: bool = False

    is_preferred: bool = False

    is_blocked: bool = False

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

    is_active: bool = True

    synced_at: datetime | None = None

    last_modified_external: datetime | None = None

    tags: list[str] = Field(default_factory=list)

    notes: str | None = None

    metadata: JsonDict = Field(default_factory=dict)
