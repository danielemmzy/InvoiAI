"""
============================================================
Audit Context

Runtime audit logging context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel


class AuditContext(BaseModel):
    """
    Audit execution context.
    """

    org_id: UUID

    user_id: UUID | None = None

    request_id: str | None = None

    session_id: str | None = None

    resource_type: str

    resource_id: UUID | None = None

    action: str

    ai_triggered: bool = False

    ai_job_id: UUID | None = None