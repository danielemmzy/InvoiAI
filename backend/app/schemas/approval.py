"""
============================================================
Approval Schemas

API request/response models.

ApprovalQueue is a VIEW, so it belongs here instead of
the domain layer.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import (
    ApprovalDecision,
    DocumentType,
    OrgRole,
    RecommendationType,
    RiskLevel,
    
)
from app.core.enum.application import ApprovalStatus

# ============================================================
# Approval Decision Request
# ============================================================

class ApprovalDecisionRequest(BaseModel):
    """
    Approve / Reject / Delegate a step.
    """

    decision: ApprovalDecision

    comment: str | None = None

    delegated_to: UUID | None = None

    delegation_reason: str | None = None


# ============================================================
# Workflow Response
# ============================================================

class ApprovalWorkflowResponse(BaseModel):
    """
    Approval workflow returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

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

    due_date: datetime | None

    escalation_due: datetime | None

    completed_at: datetime | None

    auto_approved: bool

    auto_rejected: bool

    is_urgent: bool

    metadata: dict[str, Any]

    created_at: datetime

    updated_at: datetime


# ============================================================
# Approval Step Response
# ============================================================

class ApprovalStepResponse(BaseModel):
    """
    Single workflow step.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    workflow_id: UUID

    org_id: UUID

    step_number: int

    step_name: str

    approver_id: UUID 

    approver_role: OrgRole

    spending_limit: Decimal | None

    decision: ApprovalDecision | None

    decided_at: datetime | None

    comment: str | None

    delegated_to: UUID | None

    delegated_at: datetime | None

    delegation_reason: str | None

    due_date: datetime | None

    reminder_sent_at: datetime | None

    escalated_at: datetime | None

    created_at: datetime


# ============================================================
# Approval History Response
# ============================================================

class ApprovalHistoryResponse(BaseModel):
    """
    Approval history entry.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    workflow_id: UUID

    step_id: UUID 

    org_id: UUID

    actor_id: UUID 

    action: str

    comment: str 

    old_status: ApprovalStatus 

    new_status: ApprovalStatus 
    
    metadata: dict[str, Any]

    created_at: datetime


# ============================================================
# Approval Queue (VIEW)
# ============================================================

class ApprovalQueueResponse(BaseModel):
    """
    Mirrors approval_queue view.
    """

    approver_id: UUID

    org_id: UUID

    workflow_id: UUID

    step_id: UUID

    step_name: str

    step_number: int

    due_date: datetime | None

    document_id: UUID

    document_number: str | None

    vendor_name: str | None

    total_amount: Decimal

    currency: str

    document_type: DocumentType

    # LEFT JOIN document_analyses in the live approval_queue view means
    # these three can be NULL when a step reaches approval before its
    # analysis row exists — confirmed against the real view definition.
    # Required fields here would 500 the whole endpoint on that one row.
    health_score: int | None = None

    risk_level: RiskLevel | None = None

    recommendation: RecommendationType | None = None

    is_urgent: bool

    initiated_at: datetime


# ============================================================
# Workflow List
# ============================================================

class ApprovalWorkflowListResponse(BaseModel):
    items: list[ApprovalWorkflowResponse] = Field(default_factory=list)

    total: int


# ============================================================
# Queue List
# ============================================================

class ApprovalQueueListResponse(BaseModel):
    items: list[ApprovalQueueResponse] = Field(default_factory=list)

    total: int