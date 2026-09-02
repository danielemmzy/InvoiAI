from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from pydantic import Field
from app.models.domain.base import DomainModel, TimestampedEntity
from app.core.enum.ap import APCodingSource, APCodingStatus, APDimensionType, APExceptionStatus, APExceptionType

class ChartOfAccount(TimestampedEntity):
    org_id: UUID
    external_id: str | None = None
    external_parent_id: str | None = None
    account_code: str
    account_name: str
    account_type: str
    account_subtype: str | None = None
    parent_account_id: UUID | None = None
    is_active: bool = True
    is_postable: bool = True
    source: str = "manual"

class AccountingDimension(TimestampedEntity):
    org_id: UUID
    dimension_type: APDimensionType
    external_id: str | None = None
    code: str
    name: str
    parent_id: UUID | None = None
    is_active: bool = True
    source: str = "manual"

class TaxCode(DomainModel):
    id: UUID
    org_id: UUID
    external_id: str | None = None
    code: str
    name: str
    rate: Decimal = Decimal("0")
    jurisdiction: str | None = None
    is_active: bool = True
    source: str = "manual"
    created_at: datetime

class CodingRule(TimestampedEntity):
    org_id: UUID
    vendor_id: UUID | None = None
    description_pattern: str | None = None
    sku_pattern: str | None = None
    gl_account_id: UUID | None = None
    department_id: UUID | None = None
    cost_center_id: UUID | None = None
    project_id: UUID | None = None
    tax_code_id: UUID | None = None
    priority: int = 100
    is_active: bool = True
    match_count: int = 0
    created_by: UUID | None = None

class InvoiceCoding(TimestampedEntity):
    org_id: UUID
    document_id: UUID
    line_item_id: UUID | None = None
    gl_account_id: UUID | None = None
    department_id: UUID | None = None
    cost_center_id: UUID | None = None
    project_id: UUID | None = None
    location_id: UUID | None = None
    class_id: UUID | None = None
    tax_code_id: UUID | None = None
    amount: Decimal | None = None
    confidence: Decimal = Decimal("0")
    source: APCodingSource = APCodingSource.MANUAL
    coding_rule_id: UUID | None = None
    status: APCodingStatus = APCodingStatus.PENDING
    created_by: UUID | None = None
    approved_by: UUID | None = None

class GoodsReceiptLine(DomainModel):
    id: UUID
    goods_receipt_id: UUID
    purchase_order_line_id: UUID | None = None
    description: str | None = None
    sku: str | None = None
    quantity_ordered: Decimal | None = None
    quantity_received: Decimal
    quantity_accepted: Decimal | None = None
    quantity_rejected: Decimal = Decimal("0")
    unit_of_measure: str | None = None
    unit_price: Decimal | None = None
    warehouse_location: str | None = None
    notes: str | None = None
    created_at: datetime

class GoodsReceipt(TimestampedEntity):
    org_id: UUID
    purchase_order_id: UUID | None = None
    vendor_id: UUID | None = None
    receipt_number: str | None = None
    received_at: datetime
    received_by: UUID | None = None
    location_id: UUID | None = None
    status: str = "draft"
    source: str = "manual"
    external_id: str | None = None
    notes: str | None = None
    lines: list[GoodsReceiptLine] = Field(default_factory=list)

class MatchingTolerance(TimestampedEntity):
    org_id: UUID
    scope: str = "org"
    vendor_id: UUID | None = None
    department_id: UUID | None = None
    document_type: str | None = None
    quantity_percent: Decimal = Decimal("5.0")
    price_percent: Decimal = Decimal("2.0")
    amount_absolute: Decimal = Decimal("50.0")
    currency: str = "USD"
    auto_approve_within_tol: bool = False

class InvoiceException(TimestampedEntity):
    org_id: UUID
    document_id: UUID
    exception_type: APExceptionType
    status: APExceptionStatus = APExceptionStatus.OPEN
    severity: str = "warning"
    title: str
    description: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    expected_value: str | None = None
    actual_value: str | None = None
    variance: str | None = None
    resolution_note: str | None = None
    resolved_by: UUID | None = None
    resolved_at: datetime | None = None
