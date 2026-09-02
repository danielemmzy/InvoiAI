"""
============================================================
Organization Schemas

API request/response models.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import (
    DocumentType,
    OrgRole,
    PlanType,
)


# ============================================================
# Organization Create
# ============================================================

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    currency: str
    website: str | None = None


# ============================================================
# Organization Update
# ============================================================

class OrganizationUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    currency: str | None = None
    website: str | None = None
    logo_url: str | None = None
    tax_id: str | None = None


# ============================================================
# Organization Response
# ============================================================

class OrganizationResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    name: str

    slug: str

    plan: PlanType

    industry: str | None

    company_size: str | None

    country: str | None

    currency: str

    tax_id: str | None

    logo_url: str | None

    website: str | None

    stripe_customer_id: str | None

    document_limit: int

    features: dict[str, Any]

    created_by: UUID | None

    created_at: datetime

    updated_at: datetime


# ============================================================
# Organization Settings Update
# ============================================================

class OrganizationSettingsUpdate(BaseModel):

    default_currency: str | None = None

    supported_currencies: list[str] | None = None

    timezone: str | None = None

    fiscal_year_start_month: int | None = None

    date_format: str | None = None

    number_format: str | None = None

    default_language: str | None = None

    auto_analyze: bool | None = None

    ocr_language: str | None = None

    default_industry: str | None = None

    supported_document_types: list[DocumentType] | None = None

    approval_policy: dict[str, Any] | None = None

    duplicate_threshold: Decimal | None = None

    duplicate_window_days: int | None = None

    duplicate_amount_tolerance: Decimal | None = None

    fraud_sensitivity: str | None = None

    auto_reject_fraud_score: int | None = None

    fraud_alert_email: str | None = None

    auto_create_vendors: bool | None = None

    vendor_match_threshold: Decimal | None = None

    require_vendor_verification: bool | None = None

    ai_enabled: bool | None = None

    ai_model_preference: str | None = None

    ai_temperature: Decimal | None = None

    enable_embeddings: bool | None = None

    copilot_enabled: bool | None = None

    copilot_memory_days: int | None = None

    copilot_max_context_docs: int | None = None

    analytics_enabled: bool | None = None

    analytics_retention_months: int | None = None

    email_notifications: bool | None = None

    notification_email: str | None = None

    slack_webhook_url: str | None = None

    outbound_webhook_url: str | None = None

    brand_color: str | None = None

    custom_domain: str | None = None

    sso_provider: str | None = None

    sso_config: dict[str, Any] | None = None


# ============================================================
# Organization Settings Response
# ============================================================

class OrganizationSettingsResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    default_currency: str

    supported_currencies: list[str]

    timezone: str

    fiscal_year_start_month: int

    date_format: str

    number_format: str

    default_language: str

    auto_analyze: bool

    ocr_language: str

    default_industry: str

    supported_document_types: list[DocumentType]

    approval_policy: dict[str, Any]

    duplicate_threshold: Decimal

    duplicate_window_days: int

    duplicate_amount_tolerance: Decimal

    fraud_sensitivity: str

    auto_reject_fraud_score: int

    fraud_alert_email: str | None

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

    notification_email: str | None

    slack_webhook_url: str | None

    outbound_webhook_url: str | None

    brand_color: str | None

    custom_domain: str | None

    sso_provider: str | None

    sso_config: dict[str, Any]

    created_at: datetime

    updated_at: datetime


# ============================================================
# Organization Member Response
# ============================================================

class OrganizationMemberResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    user_id: UUID

    role: OrgRole

    department: str | None

    cost_center: str | None

    spending_limit: Decimal | None

    invited_by: UUID | None

    invite_email: str | None

    invite_expires_at: datetime | None

    is_active: bool

    deactivated_at: datetime | None

    deactivated_by: UUID | None

    joined_at: datetime | None

    created_at: datetime

    updated_at: datetime


# ============================================================
# Lists
# ============================================================

class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse] = Field(default_factory=list)
    total: int


class OrganizationMemberListResponse(BaseModel):
    items: list[OrganizationMemberResponse] = Field(default_factory=list)
    total: int

# ============================================================
# Organization Usage
# ============================================================

class OrganizationUsageResponse(BaseModel):
    """
    API response for organization usage.
    """

    id: UUID

    org_id: UUID

    month: str

    documents_processed: int

    storage_used_bytes: int

    ai_tokens_used: int

    api_calls: int

    ai_cost_usd: Decimal

    created_by: UUID | None = None

    created_at: datetime

    updated_at: datetime