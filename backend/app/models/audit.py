# ============================================================
# app/models/audit.py
#
# Enterprise audit models
#
# Every important action in the system is permanently recorded.
#
# Used for:
# - Compliance
# - Enterprise customers
# - Security investigations
# - AI traceability
# ============================================================

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.enum.database import AuditAction

# ============================================================
# Audit Entry
# ============================================================


class AuditEntry(BaseModel):
    """
    Permanent audit log.
    """

    id: str

    org_id: str

    user_id: Optional[str]

    action: AuditAction

    entity_type: str

    entity_id: Optional[str]

    description: Optional[str]

    old_values: Optional[dict[str, Any]]

    new_values: Optional[dict[str, Any]]

    ip_address: Optional[str]

    user_agent: Optional[str]

    device: Optional[str]

    browser: Optional[str]

    country: Optional[str]

    request_id: Optional[str]

    ai_model: Optional[str]

    engine_version: Optional[str]

    analysis_version: Optional[str]

    prompt_version: Optional[str]

    created_at: Optional[datetime]


# ============================================================
# Audit Summary
# ============================================================


class AuditSummary(BaseModel):

    id: str

    action: AuditAction

    entity_type: str

    entity_id: Optional[str]

    description: Optional[str]

    created_at: Optional[datetime]


# ============================================================
# Audit Page
# ============================================================


class AuditPage(BaseModel):

    logs: list[AuditSummary]

    count: int

    offset: int

    limit: int


# ============================================================
# Audit Filters
# ============================================================


class AuditFilter(BaseModel):

    action: Optional[AuditAction] = None

    entity_type: Optional[str] = None

    user_id: Optional[str] = None

    from_date: Optional[datetime] = None

    to_date: Optional[datetime] = None


# ============================================================
# AI Audit
# ============================================================


class AIAudit(BaseModel):
    """
    Records AI decisions for reproducibility.
    """

    analysis_id: str

    model: str

    engine_version: str

    analysis_version: str

    prompt_version: str

    temperature: float

    tokens_used: Optional[int]

    processing_ms: Optional[int]

    created_at: Optional[datetime]
