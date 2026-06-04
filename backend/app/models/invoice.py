from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


# ── Industry registry ──────────────────────────────────────────────────────────
# Single source of truth for supported industries.
# To add a new industry: just add it here. Nothing else changes.
# Frontend reads this list to build the dropdown.
SUPPORTED_INDUSTRIES = [
    "general",
    "accounting",
    "auditing",
    "tax_compliance",
    "legal_services",
    "ecommerce",
    "retail",
    "wholesale",
    "construction",
    "architecture_engineering",
    "healthcare",
    "logistics",
    "manufacturing",
    "saas_it",
    "marketing_advertising",
    "real_estate",
    "import_export",
    "education",
    "hospitality",
    "insurance",
]

# Human-readable labels for the frontend dropdown
INDUSTRY_LABELS: dict[str, str] = {
    "general": "General",
    "accounting": "Accounting",
    "auditing": "Auditing",
    "tax_compliance": "Tax & Compliance",
    "legal_services": "Legal Services",
    "ecommerce": "E-commerce",
    "retail": "Retail",
    "wholesale": "Wholesale / Distribution",
    "construction": "Construction",
    "architecture_engineering": "Architecture & Engineering",
    "healthcare": "Healthcare",
    "logistics": "Logistics / Shipping",
    "manufacturing": "Manufacturing",
    "saas_it": "SaaS / IT Services",
    "marketing_advertising": "Marketing & Advertising",
    "real_estate": "Real Estate",
    "import_export": "Import / Export",
    "education": "Education & Training",
    "hospitality": "Hospitality",
    "insurance": "Insurance",
}


# ── Core document models ───────────────────────────────────────────────────────

class StructuredDocument(BaseModel):
    """
    The universal output model for ANY document from ANY industry.

    GPT decides what sections and fields exist based on the document.
    We don't constrain the shape — we store whatever GPT finds.

    sections: dict where each key is a section name (e.g. "line_items",
              "engagement_details", "findings") and value is either:
              - a dict (single section with fields)
              - a list of dicts (repeating rows like line items)

    raw_totals: any monetary totals GPT finds — used for validation
                without us knowing the exact field names in advance.
    """
    industry: str
    document_type: str
    sections: dict[str, Any] = Field(default_factory=dict)
    raw_totals: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: Optional[str] = None  # "high" | "medium" | "low"


class DocumentRecord(BaseModel):
    id: str
    user_id: str
    file_url: str
    file_name: str
    file_type: str
    industry: str
    document_type: Optional[str] = None
    structured_data: Optional[StructuredDocument] = None
    status: str = "processing"
    validation_warnings: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    invoice_id: str
    status: str
    document_type: Optional[str] = None
    structured_data: Optional[StructuredDocument] = None
    validation_warnings: list[str] = Field(default_factory=list)


class HistoryItem(BaseModel):
    id: str
    file_name: str
    file_type: str
    industry: str
    document_type: Optional[str] = None
    status: str
    validation_warnings: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class IndustriesResponse(BaseModel):
    industries: list[dict[str, str]]