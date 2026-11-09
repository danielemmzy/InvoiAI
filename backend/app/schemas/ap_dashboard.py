from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APDashboardFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    vendor_id: UUID | None = None
    status: str | None = None
    priority: str | None = None
    # Legacy transaction-currency filter. It only includes invoices whose original currency matches.
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    # Reporting currency converts invoice amounts without changing the stored transaction currency.
    reporting_currency: str | None = Field(default=None, min_length=3, max_length=3)
    search: str | None = None


class APMonthPoint(BaseModel):
    month: str
    billed: float
    paid: float


class APTurnoverPoint(BaseModel):
    month: str
    days: float


class APCurrencyAmount(BaseModel):
    currency: str
    amount: float


class APSummaryResponse(BaseModel):
    total_vendors: int
    open_vendors: int
    total_invoices: int
    open_invoices: int
    total_amount: float
    total_paid: float
    open_amount: float
    overdue_amount: float
    currency: str
    payables_by_month: list[APMonthPoint]
    payable_turnover_days: float
    payable_turnover_trend: list[APTurnoverPoint]
    by_currency: list[APCurrencyAmount]


class APInvoiceRowResponse(BaseModel):
    id: UUID
    vendor_id: UUID | str
    vendor_name: str
    invoice_number: str | None
    amount: float
    currency: str
    status: str
    priority: str
    tags: list[str]
    issue_date: date | None
    due_date: date | None
    health_score: int | None = None
    risk_level: str | None = None
    document_id: UUID
    reporting_amount: float | None = None
    reporting_currency: str | None = None
    fx_rate: float | None = None
    fx_rate_date: date | None = None


class APInvoiceListResponse(BaseModel):
    items: list[APInvoiceRowResponse]
    total: int
    limit: int
    offset: int


class APTopVendorResponse(BaseModel):
    vendor_id: UUID | str
    vendor_name: str
    current_balance: float
    overdue_balance: float
    currency: str
    risk_score: int
    risk_level: str


class APAgingBucketResponse(BaseModel):
    bucket: str
    label: str
    amount: float
    invoice_count: int


class APAgingRowResponse(BaseModel):
    vendor_id: UUID | str
    vendor_name: str
    current: float
    d1_30: float
    d31_60: float
    d61_90: float
    d90_plus: float
    total: float


class APAgingResponse(BaseModel):
    buckets: list[APAgingBucketResponse]
    rows: list[APAgingRowResponse]
    currency: str
