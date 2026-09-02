"""
============================================================
Audit Schemas

API request/response models.
============================================================
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Audit Filters
# ============================================================

class AuditLogFilter(BaseModel):
    """
    Filter audit logs.
    """

    user_id: UUID | None = None

    action: str | None = None

    resource_type: str | None = None

    resource_id: UUID | None = None

    ai_triggered: bool | None = None

    start_date: datetime | None = None

    end_date: datetime | None = None

    page: int = 1

    page_size: int = 20


# ============================================================
# Audit Response
# ============================================================

class AuditLogResponse(BaseModel):
    """
    Audit log returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    user_id: UUID | None

    action: str

    resource_type: str

    resource_id: UUID | None

    old_values: dict[str, Any]

    new_values: dict[str, Any]

    diff: dict[str, Any]

    request_id: str | None

    session_id: str | None

    ip_address: str | None

    user_agent: str | None

    browser: str | None

    device_type: str | None

    os: str | None

    country: str | None

    city: str | None

    ai_triggered: bool

    ai_model_used: str | None

    ai_prompt_version: str | None

    ai_job_id: UUID | None

    metadata: dict[str, Any]

    created_at: datetime


# ============================================================
# Audit List
# ============================================================

class AuditLogListResponse(BaseModel):
    """
    Paginated audit logs.
    """

    items: list[AuditLogResponse] = Field(default_factory=list)

    total: int

    page: int

    page_size: int