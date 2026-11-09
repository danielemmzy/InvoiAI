"""Approval rows must map into the domain models without timestamp drift.

The workflow row is inserted before its steps, then read back. If the domain
model forbids a database timestamp column, the insert succeeds but the caller
gets a validation error and the workflow is left without steps.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.mappers.approval_mapper import ApprovalStepMapper, ApprovalWorkflowMapper


def _workflow_row():
    now = datetime.now(UTC)
    return {
        "id": str(uuid4()),
        "org_id": str(uuid4()),
        "document_id": str(uuid4()),
        "analysis_id": str(uuid4()),
        "status": "in_review",
        "current_step": 1,
        "current_stage": 1,
        "total_steps": 1,
        "workflow_type": "bill",
        "execution_mode": "sequential",
        "document_amount": 957.0,
        "document_type": "invoice",
        "vendor_name": "J/S",
        "risk_level": "medium",
        "initiated_by": str(uuid4()),
        "initiated_at": now,
        "due_date": now,
        "escalation_due": now,
        "completed_at": None,
        "auto_approved": False,
        "auto_rejected": False,
        "is_urgent": False,
        "metadata": {"ap_automation": True},
        "created_at": now,
        "updated_at": now,
    }


def _step_row():
    now = datetime.now(UTC)
    return {
        "id": str(uuid4()),
        "workflow_id": str(uuid4()),
        "org_id": str(uuid4()),
        "step_number": 1,
        "stage_number": 1,
        "step_name": "AP Approval",
        "approver_id": str(uuid4()),
        "approver_role": "owner",
        "approver_group_id": None,
        "claimed_by": None,
        "claimed_at": None,
        "auto_escalated": False,
        "spending_limit": None,
        "decision": "pending",
        "decided_at": None,
        "comment": None,
        "delegated_to": None,
        "delegated_at": None,
        "delegation_reason": None,
        "due_date": now,
        "reminder_sent_at": None,
        "escalated_at": None,
        "created_at": now,
        "updated_at": now,
    }


def test_workflow_row_with_database_timestamps_maps_to_domain():
    workflow = ApprovalWorkflowMapper.to_domain(_workflow_row())

    assert workflow is not None
    assert workflow.created_at is not None
    assert workflow.updated_at is not None


def test_step_row_with_database_timestamps_maps_to_domain():
    step = ApprovalStepMapper.to_domain(_step_row())

    assert step is not None
    assert step.created_at is not None
    assert step.updated_at is not None
