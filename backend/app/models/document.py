# ============================================================
# app/models/document.py
# Document API models
#
# Supports:
# - invoices
# - receipts
# - purchase orders
# - quotations
# - contracts
# - statements
# - spreadsheets
#
# AI analysis is intentionally separated.
# Upload != Analysis.
# ============================================================

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# Upload
# ============================================================

class DocumentUploadResult(BaseModel):
    """
    Returned immediately after upload.

    This does NOT contain AI analysis.
    OCR and AI happen asynchronously.
    """

    document_id: str

    job_id: Optional[str] = None

    status: str

    pipeline_stage: str

    message: str

    created_at: datetime


# ============================================================
# Document Summary
# ============================================================

class DocumentSummary(BaseModel):

    id: str

    file_name: str

    file_type: str

    document_type: Optional[str]

    vendor_name: Optional[str]

    document_number: Optional[str]

    document_date: Optional[date]

    total_amount: Optional[float]

    currency: str

    status: str

    pipeline_stage: str

    created_at: Optional[datetime]

    is_archived: bool


class DocumentPage(BaseModel):

    documents: list[DocumentSummary]

    count: int

    offset: int

    limit: int


# ============================================================
# Document Detail
# ============================================================

class DocumentDetail(BaseModel):

    id: str

    org_id: str

    vendor_id: Optional[str]

    created_by: Optional[str]

    uploaded_by: Optional[str]

    source: str

    industry: str

    document_type: Optional[str]

    file_name: str

    file_url: Optional[str]

    file_size: Optional[int]

    mime_type: Optional[str]

    file_hash: Optional[str]

    file_type: str

    vendor_name: Optional[str]

    document_number: Optional[str]

    document_date: Optional[date]

    due_date: Optional[date]

    currency: str

    subtotal: Optional[float]

    tax_amount: Optional[float]

    total_amount: Optional[float]

    extraction_confidence: Optional[float]

    structured_data: Optional[dict]

    validation_warnings: list[str] = []

    status: str

    pipeline_stage: str

    is_archived: bool

    sheets_url: Optional[str]

    created_at: Optional[datetime]

    updated_at: Optional[datetime]

    processed_at: Optional[datetime]

    analysis: Optional["DocumentAnalysisReference"] = None


# ============================================================
# Lightweight AI reference
# ============================================================

class DocumentAnalysisReference(BaseModel):

    analysis_id: str

    overall_score: Optional[int]

    health_score: Optional[int]

    risk_level: Optional[str]

    recommendation: Optional[str]

    completed_at: Optional[datetime]


DocumentDetail.model_rebuild()