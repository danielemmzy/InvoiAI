"""
============================================================
Approval Domain Models

Mirror PostgreSQL approval tables.

Tables
------
- approval_workflows
- approval_steps
- approval_history

Notes
-----
- approval_queue is a PostgreSQL VIEW and therefore belongs
  in schemas, not the domain layer.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.core.enum.database import (
    ApprovalDecision,
    DocumentType,
    OrgRole,
    RecommendationType,
    RiskLevel,
)
from app.core.enum.application import ApprovalStatus
from app.models.domain.base import DomainModel


# ============================================================
# Approval Workflow
# ============================================================

class ApprovalWorkflow(DomainModel):
    """
    Mirrors approval_workflows.
    """

    id: UUID

    org_id: UUID

    document_id: UUID

    analysis_id: UUID

    status: ApprovalStatus

    current_step: int

    total_steps: int

    document_amount: Decimal

    document_type: DocumentType

    vendor_name: str

    risk_level: RiskLevel

    initiated_by: UUID

    initiated_at: datetime

    due_date: datetime | None = None

    escalation_due: datetime | None = None

    completed_at: datetime | None = None

    auto_approved: bool

    auto_rejected: bool

    is_urgent: bool

    metadata: dict[str, Any]


# ============================================================
# Approval Step
# ============================================================

class ApprovalStep(DomainModel):
    """
    Mirrors approval_steps.
    """

    id: UUID = Field(default_factory=uuid4)

    workflow_id: UUID

    org_id: UUID

    step_number: int

    step_name: str

    approver_id: UUID

    approver_role: OrgRole

    spending_limit: Decimal | None = None

    decision: ApprovalDecision | None = None

    decided_at: datetime | None = None

    comment: str | None = None

    delegated_to: UUID | None = None

    delegated_at: datetime | None = None

    delegation_reason: str | None = None

    due_date: datetime | None = None

    reminder_sent_at: datetime | None = None

    escalated_at: datetime | None = None

    created_at: datetime


# ============================================================
# Approval History
# ============================================================

class ApprovalHistory(DomainModel):
    """
    Mirrors approval_history.
    """

    id: UUID

    workflow_id: UUID

    step_id: UUID

    org_id: UUID

    actor_id: UUID

    action: str

    comment: str | None = None

    old_status: ApprovalStatus

    new_status: ApprovalStatus

    metadata: dict[str, Any]

    created_at: datetime