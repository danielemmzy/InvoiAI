# ============================================================
# Document
# ============================================================

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.core.enum.database import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    FileType,
    PipelineStage,
    OCREngineType,
    InvoiceStatus,
)

from app.models.domain.base import DomainModel


JsonDict = dict[str, Any]


class Document(DomainModel):
    """
    Mirrors documents table.
    """

    id: UUID

    org_id: UUID

    created_by: UUID | None = None

    vendor_id: UUID | None = None

    purchase_order_id: UUID | None = None

    source: DocumentSource

    document_type: DocumentType

    industry: str

    external_id: str | None = None

    external_url: str | None = None

    external_source_data: JsonDict = Field(default_factory=dict)

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

    # =====================================================
    # Financial
    # =====================================================

    paid_amount: Decimal = Decimal("0")

    balance_due: Decimal | None = None

    payment_status: str = "unpaid"

    paid_at: datetime | None = None

    payment_terms: str | None = None

    payment_method: str | None = None

    # =====================================================
    # Processing
    # =====================================================

    pipeline_stage: PipelineStage

    status: DocumentStatus

    validation_warnings: list[str] = Field(default_factory=list)

    error_message: str | None = None

    retry_count: int

    last_retry_at: datetime | None = None

    # =====================================================
    # Export
    # =====================================================

    sheets_url: str | None = None

    last_exported_at: datetime | None = None

    last_exported_format: str | None = None

    last_exported_by: UUID | None = None

    # =====================================================
    # Archive
    # =====================================================

    is_archived: bool

    archived_at: datetime | None = None

    archived_by: UUID | None = None

    archive_reason: str | None = None

    # =====================================================
    # Misc
    # =====================================================

    notes: str | None = None

    created_at: datetime

    updated_at: datetime


class DocumentLineItem(DomainModel):
    """
    Mirrors document_line_items table.
    """

    id: UUID

    document_id: UUID

    org_id: UUID

    description: str

    quantity: Decimal

    unit_price: Decimal

    amount: Decimal

    tax_rate: Decimal | None = None

    tax_amount: Decimal | None = None

    discount: Decimal | None = None

    sku: str | None = None

    product_code: str | None = None

    unit_type: str | None = None

    category: str | None = None

    sub_category: str | None = None

    gl_account: str | None = None

    cost_center: str | None = None

    project_code: str | None = None

    line_order: int

    metadata: JsonDict = Field(default_factory=dict)

    created_at: datetime

# ============================================================
# OCR Result
# ============================================================

class OCRResult(DomainModel):
    """
    Mirrors ocr_results table.
    """

    id: UUID = Field(default_factory=uuid4)

    document_id: UUID

    org_id: UUID

    raw_text: str

    page_count: int

    pages: list[dict[str, Any]] = Field(default_factory=list)

    tables_detected: list[dict[str, Any]] = Field(default_factory=list)

    key_value_pairs: JsonDict = Field(default_factory=dict)

    language_detected: str | None = None

    is_handwritten: bool

    is_scanned: bool

    has_tables: bool

    has_signatures: bool

    image_quality: int

    engine: OCREngineType

    engine_version: str | None = None

    confidence_score: Decimal

    processing_ms: int

    tokens_used: int

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============================================================
# Purchase Order
# ============================================================

class PurchaseOrder(DomainModel):
    """
    Mirrors purchase_orders table.
    """

    id: UUID

    org_id: UUID

    vendor_id: UUID

    po_number: str

    description: str | None = None

    amount: Decimal

    currency: str

    issued_date: date | None = None

    expiry_date: date | None = None

    is_open: bool

    matched_amount: Decimal

    created_by: UUID | None = None

    external_id: str | None = None

    metadata: JsonDict = Field(default_factory=dict)

    created_at: datetime

    updated_at: datetime

# ============================================================
# Invoice (Legacy)
# ============================================================

class Invoice(DomainModel):
    """
    Mirrors invoices table.

    Legacy table retained for backwards compatibility.
    """

    id: UUID

    user_id: UUID

    file_url: str

    file_name: str

    industry: str

    document_type: str

    structured_data: JsonDict = Field(default_factory=dict)

    status: InvoiceStatus

    validation_warnings: list[str] = Field(default_factory=list)

    sheets_url: str | None = None

    created_at: datetime

    raw_text: str | None = None


# ============================================================
# Invoice Raw Text (Legacy)
# ============================================================

class InvoiceRawText(DomainModel):
    """
    Mirrors invoice_raw_text table.

    Legacy OCR text storage.
    """

    invoice_id: UUID

    raw_text: str

    created_at: datetime