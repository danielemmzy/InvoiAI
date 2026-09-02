"""
============================================================
Approval Context

Runtime approval workflow context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel

from app.core.enum.database import ApprovalDecision
from app.core.enum.application import ApprovalStatus



class ApprovalContext(BaseModel):
    """
    Current approval workflow.
    """

    workflow_id: UUID

    document_id: UUID

    org_id: UUID

    current_step: int

    total_steps: int

    status: ApprovalStatus

    approver_id: UUID | None = None

    decision: ApprovalDecision | None = None

    is_urgent: bool = False