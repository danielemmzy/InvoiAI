"""
============================================================
Document Schemas

API request/response models.
============================================================
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    FileType,
    OCREngineType,
    PipelineStage,
    RecommendationType,
    RiskLevel,
)

# ============================================================
# Document Create
# ============================================================

class DocumentCreate(BaseModel):
    """
    Create a document.
    """

    vendor_id: UUID | None = None

    purchase_order_id: UUID | None = None

    source: DocumentSource

    document_type: DocumentType

    industry: str

    external_id: str | None = None

    external_url: str | None = None

    external_source_data: dict[str, Any] = Field(default_factory=dict)

    file_url: str

    file_name: str

    file_type: FileType

    file_size_bytes: int | None = None

    file_hash: str | None = None

    vendor_name: str | None = None

    document_number: str | None = None

    document_date: date | None = None

    due_date: date | None = None

    currency: str

    subtotal: Decimal | None = None

    tax_amount: Decimal | None = None

    tax_rate: Decimal | None = None

    discount_amount: Decimal | None = None

    total_amount: Decimal | None = None

    amount_paid: Decimal | None = None

    amount_due: Decimal | None = None

    payment_terms: str | None = None

    payment_method: str | None = None

    notes: str | None = None

# ============================================================
# Document Update
# ============================================================

class DocumentUpdate(BaseModel):
    """
    Update an existing document.
    """

    vendor_id: UUID | None = None

    purchase_order_id: UUID | None = None

    document_type: DocumentType | None = None

    industry: str | None = None

    external_id: str | None = None

    external_url: str | None = None

    external_source_data: dict[str, Any] | None = None

    vendor_name: str | None = None

    document_number: str | None = None

    document_date: date | None = None

    due_date: date | None = None

    currency: str | None = None

    subtotal: Decimal | None = None

    tax_amount: Decimal | None = None

    tax_rate: Decimal | None = None

    discount_amount: Decimal | None = None

    total_amount: Decimal | None = None

    amount_paid: Decimal | None = None

    amount_due: Decimal | None = None

    payment_terms: str | None = None

    payment_method: str | None = None

    pipeline_stage: PipelineStage | None = None

    status: DocumentStatus | None = None

    validation_warnings: list[str] | None = None

    error_message: str | None = None

    retry_count: int | None = None

    last_retry_at: datetime | None = None

    sheets_url: str | None = None

    last_exported_at: datetime | None = None

    last_exported_format: str | None = None

    last_exported_by: UUID | None = None

    is_archived: bool | None = None

    archived_at: datetime | None = None

    archived_by: UUID | None = None

    archive_reason: str | None = None

    notes: str | None = None

# ============================================================
# Document Response
# ============================================================

class DocumentResponse(BaseModel):
    """
    Document returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    created_by: UUID | None

    vendor_id: UUID | None

    purchase_order_id: UUID | None

    source: DocumentSource

    document_type: DocumentType

    industry: str

    external_id: str | None

    external_url: str | None

    external_source_data: dict[str, Any]

    file_url: str

    file_name: str

    file_type: FileType

    file_size_bytes: int | None

    file_hash: str | None

    vendor_name: str | None

    document_number: str | None

    document_date: date | None

    due_date: date | None

    currency: str

    subtotal: Decimal | None

    tax_amount: Decimal | None

    tax_rate: Decimal | None

    discount_amount: Decimal | None

    total_amount: Decimal | None

    amount_paid: Decimal | None

    amount_due: Decimal | None

    payment_terms: str | None

    payment_method: str | None

    pipeline_stage: PipelineStage

    status: DocumentStatus

    validation_warnings: list[str]

    error_message: str | None

    retry_count: int

    last_retry_at: datetime | None

    sheets_url: str | None

    last_exported_at: datetime | None

    last_exported_format: str | None

    last_exported_by: UUID | None

    is_archived: bool

    archived_at: datetime | None

    archived_by: UUID | None

    archive_reason: str | None

    notes: str | None

    created_at: datetime

    updated_at: datetime

# ============================================================
# Document Analysis Response
# ============================================================

class DocumentAnalysisResponse(BaseModel):
    """
    AI analysis returned for a document.
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

    positive_signals: list[str]

    action_items: list[str]

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

    model: str

    engine_version: str

    analysis_version: str

    prompt_version: str

    temperature: Decimal | None

    processing_ms: int

    tokens_used: int

    tokens_cost_usd: Decimal | None

    created_at: datetime

    updated_at: datetime

# ============================================================
# OCR Result Response
# ============================================================

class OCRResultResponse(BaseModel):
    """
    OCR result returned for a document.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    document_id: UUID

    org_id: UUID

    raw_text: str

    page_count: int

    pages: dict[str, Any]

    tables_detected: dict[str, Any]

    key_value_pairs: dict[str, Any]

    language_detected: str | None

    is_handwritten: bool

    is_scanned: bool

    has_tables: bool

    has_signatures: bool

    image_quality: int

    engine: OCREngineType

    engine_version: str

    confidence_score: Decimal

    processing_ms: int

    tokens_used: int

    created_at: datetime

# ============================================================
# Purchase Order Response
# ============================================================

class PurchaseOrderResponse(BaseModel):
    """
    Purchase order returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    vendor_id: UUID

    po_number: str

    description: str | None

    amount: Decimal

    currency: str

    issued_date: date | None

    expiry_date: date | None

    is_open: bool

    matched_amount: Decimal

    created_by: UUID | None

    external_id: str | None

    metadata: dict[str, Any]

    created_at: datetime

    updated_at: datetime

# ============================================================
# Invoice Response
# ============================================================

class InvoiceResponse(BaseModel):
    """
    Legacy invoice response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    user_id: UUID

    file_url: str

    file_name: str

    industry: str

    document_type: str

    structured_data: dict[str, Any]

    status: str

    validation_warnings: list[str]

    sheets_url: str | None

    created_at: datetime

    raw_text: str | None

# ============================================================
# Invoice Raw Text Response
# ============================================================

class InvoiceRawTextResponse(BaseModel):
    """
    Raw OCR text associated with a legacy invoice.
    """

    model_config = ConfigDict(from_attributes=True)

    invoice_id: UUID

    raw_text: str

    created_at: datetime

# ============================================================
# Document Line Item Response
# ============================================================

class DocumentLineItemResponse(BaseModel):
    """
    Individual extracted line item.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    document_id: UUID

    org_id: UUID

    description: str

    quantity: Decimal | None

    unit_price: Decimal | None

    amount: Decimal | None

    tax_rate: Decimal | None

    tax_amount: Decimal | None

    discount: Decimal | None

    sku: str | None

    product_code: str | None

    unit_type: str | None

    category: str | None

    sub_category: str | None

    gl_account: str | None

    cost_center: str | None

    project_code: str | None

    line_order: int

    metadata: dict[str, Any]

    created_at: datetime