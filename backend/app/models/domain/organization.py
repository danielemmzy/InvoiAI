"""
============================================================
Organization Domain Models

These models mirror the PostgreSQL tables:

- organizations
- organization_settings
- org_members
- organization_usage
============================================================
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.database import OrgRole, PlanType
from app.models.domain.base import TimestampedEntity


JsonDict = dict[str, Any]


# ============================================================
# Organization
# ============================================================

class Organization(TimestampedEntity):
    """
    Mirrors the organizations table.
    """

    name: str
    slug: str
    plan: PlanType
    ai_summary: str | None = None
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    currency: str
    tax_id: str | None = None
    logo_url: str | None = None
    website: str | None = None
    stripe_customer_id: str | None = None
    document_limit: int
    features: JsonDict = Field(default_factory=dict)
    created_by: UUID | None = None


# ============================================================
# Organization Settings
# ============================================================

class OrganizationSettings(TimestampedEntity):
    """
    Mirrors the organization_settings table.
    """

    org_id: UUID
    default_currency: str
    supported_currencies: list[str] = Field(default_factory=list)
    timezone: str
    fiscal_year_start_month: int
    date_format: str
    number_format: str
    default_language: str
    auto_analyze: bool
    ocr_language: str
    default_industry: str
    supported_document_types: list[str] = Field(default_factory=list)
    approval_policy: JsonDict = Field(default_factory=dict)
    duplicate_threshold: Decimal
    duplicate_window_days: int
    duplicate_amount_tolerance: Decimal
    fraud_sensitivity: str
    auto_reject_fraud_score: int
    fraud_alert_email: str | None = None
    auto_create_vendors: bool
    vendor_match_threshold: Decimal
    require_vendor_verification: bool
    ai_enabled: bool
    ai_model_preference: str
    ai_temperature: Decimal
    enable_embeddings: bool
    copilot_enabled: bool
    copilot_memory_days: int
    copilot_max_context_docs: int
    analytics_enabled: bool
    analytics_retention_months: int
    email_notifications: bool
    notification_email: str | None = None
    slack_webhook_url: str | None = None
    outbound_webhook_url: str | None = None
    brand_color: str | None = None
    custom_domain: str | None = None
    sso_provider: str | None = None
    sso_config: JsonDict = Field(default_factory=dict)


# ============================================================
# Organization Member
# ============================================================

class OrganizationMember(TimestampedEntity):
    """
    Mirrors the org_members table.
    """

    org_id: UUID
    user_id: UUID
    role: OrgRole
    department: str | None = None
    cost_center: str | None = None
    spending_limit: Decimal | None = None
    invited_by: UUID | None = None
    invite_email: str | None = None
    invite_token: str | None = None
    invite_expires_at: datetime | None = None
    is_active: bool
    deactivated_at: datetime | None = None
    deactivated_by: UUID | None = None
    joined_at: datetime | None = None


# ============================================================
# Organization Usage
# ============================================================

class OrganizationUsage(TimestampedEntity):
    """
    Mirrors the public.organization_usage table.

    PostgreSQL:
        month DATE NOT NULL

    The application therefore uses datetime.date rather than str.
    """

    org_id: UUID

    month: date

    documents_processed: int

    storage_used_bytes: int

    ai_tokens_used: int

    api_calls: int

    ai_cost_usd: Decimal

    created_by: UUID | None = None