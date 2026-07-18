# ============================================================
# app/models/approval.py
# Approval workflow models
#
# Business domain:
# Document
#      ↓
# Approval Workflow
#      ↓
# Approval Steps
#      ↓
# Approval Decisions
#      ↓
# Approval History
# ============================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.enums import (
    ApprovalDecision,
    ApprovalStatus,
    OrgRole,
)


# ============================================================
# Workflow
# ============================================================

class ApprovalWorkflowCreate(BaseModel):
    """
    Create a workflow for an organization.
    """

    name: str = Field(..., min_length=2, max_length=100)

    description: Optional[str] = None

    is_default: bool = False

    is_active: bool = True


class ApprovalWorkflowUpdate(BaseModel):
    """
    Update workflow metadata.
    """

    name: Optional[str] = Field(None, min_length=2, max_length=100)

    description: Optional[str] = None

    is_default: Optional[bool] = None

    is_active: Optional[bool] = None


class ApprovalWorkflow(BaseModel):

    id: str

    org_id: str

    name: str

    description: Optional[str]

    is_default: bool

    is_active: bool

    total_steps: int

    created_by: Optional[str]

    created_at: Optional[datetime]

    updated_at: Optional[datetime]


# ============================================================
# Workflow Step
# ============================================================

class ApprovalStepCreate(BaseModel):
    """
    One approval stage.
    """

    step_order: int = Field(..., ge=1)

    role: OrgRole

    minimum_amount: Optional[float] = Field(None, ge=0)

    maximum_amount: Optional[float] = Field(None, ge=0)

    is_required: bool = True


class ApprovalStepUpdate(BaseModel):

    role: Optional[OrgRole] = None

    minimum_amount: Optional[float] = Field(None, ge=0)

    maximum_amount: Optional[float] = Field(None, ge=0)

    is_required: Optional[bool] = None


class ApprovalStep(BaseModel):

    id: str

    workflow_id: str

    step_order: int

    role: OrgRole

    minimum_amount: Optional[float]

    maximum_amount: Optional[float]

    is_required: bool

    created_at: Optional[datetime]


# ============================================================
# Approval Decision
# ============================================================

class ApprovalDecisionRequest(BaseModel):
    """
    Approve / Reject / Escalate.
    """

    decision: ApprovalDecision

    comments: Optional[str] = Field(
        None,
        max_length=1000,
    )


# ============================================================
# Approval History
# ============================================================

class ApprovalHistory(BaseModel):

    id: str

    workflow_id: str

    document_id: str

    step_id: str

    user_id: str

    role: OrgRole

    decision: ApprovalDecision

    status: ApprovalStatus

    comments: Optional[str]

    decided_at: Optional[datetime]


# ============================================================
# Approval Summary
# ============================================================

class ApprovalSummary(BaseModel):
    """
    Embedded inside DocumentDetail later.
    """

    workflow_id: Optional[str]

    current_step: Optional[int]

    total_steps: int

    status: ApprovalStatus

    pending_role: Optional[OrgRole]

    approved_by: list[str] = []

    rejected_by: Optional[str]

    completed_at: Optional[datetime]