"""
============================================================
Audit Domain Models

Mirror PostgreSQL tables.

- audit_logs
============================================================
"""

from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.domain.base import DomainModel


class AuditLog(DomainModel):
    """
    Mirrors audit_logs.
    """

    id: UUID

    org_id: UUID

    user_id: UUID | None = None

    action: str

    resource_type: str

    resource_id: UUID | None = None

    old_values: dict[str, Any] = Field(default_factory=dict)

    new_values: dict[str, Any] = Field(default_factory=dict)

    diff: dict[str, Any] = Field(default_factory=dict)

    request_id: str | None = None

    session_id: str | None = None

    ip_address: str | None = None

    user_agent: str | None = None

    browser: str | None = None

    device_type: str | None = None

    os: str | None = None

    country: str | None = None

    city: str | None = None

    ai_triggered: bool

    ai_model_used: str | None = None

    ai_prompt_version: str | None = None

    ai_job_id: UUID | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: Any