"""
============================================================
Approval Workflow Service

Application/service layer for approval workflows.

Responsibilities:
- Create approval workflows
- Retrieve workflows
- List organization workflows
- Update workflow status
- Complete/reject workflows
- Validate workflow state before transitions
- Coordinate approval_engine.py
- Keep persistence inside repositories

No direct database queries.
No Supabase calls.
No HTTP/API logic.
No worker/background-task logic.
============================================================
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.enum.application import ApprovalStatus
from app.core.enum.database import DocumentType, RiskLevel
from app.models.domain.approval import ApprovalWorkflow
from app.repositories.approval.workflow_repository import (
    ApprovalWorkflowRepository,
)


class ApprovalWorkflowService:
    """
    Application service responsible for approval workflows.

    This service orchestrates workflow-level operations.
    """

    def __init__(
        self,
        workflow_repository: ApprovalWorkflowRepository,
    ) -> None:
        self.workflow_repository = workflow_repository

    # =========================================================
    # CREATE
    # =========================================================

    async def create_workflow(
        self,
        *,
        org_id: UUID,
        document_id: UUID,
        analysis_id: UUID,
        document_amount: Decimal,
        document_type: DocumentType,
        vendor_name: str,
        risk_level: RiskLevel,
        initiated_by: UUID,
        total_steps: int,
        due_date=None,
        escalation_due=None,
        auto_approved: bool = False,
        auto_rejected: bool = False,
        is_urgent: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalWorkflow:
        """
        Create a new approval workflow.

        A newly created workflow starts in PENDING state and
        begins at step 1.
        """

        if total_steps <= 0:
            raise ValueError(
                "Approval workflow must contain at least one step."
            )

        if document_amount < 0:
            raise ValueError(
                "Document amount cannot be negative."
            )

        if auto_approved and auto_rejected:
            raise ValueError(
                "A workflow cannot be both auto-approved and auto-rejected."
            )

        existing = await self.workflow_repository.get_document_workflow(
            document_id
        )

        if existing is not None:
            raise ValueError(
                "An approval workflow already exists for this document."
            )

        workflow = ApprovalWorkflow(
            org_id=org_id,
            document_id=document_id,
            analysis_id=analysis_id,
            status=ApprovalStatus.PENDING,
            current_step=1,
            total_steps=total_steps,
            document_amount=document_amount,
            document_type=document_type,
            vendor_name=vendor_name,
            risk_level=risk_level,
            initiated_by=initiated_by,
            due_date=due_date,
            escalation_due=escalation_due,
            auto_approved=auto_approved,
            auto_rejected=auto_rejected,
            is_urgent=is_urgent,
            metadata=metadata or {},
        )

        created = await self.workflow_repository.create_workflow(
            workflow
        )

        if created is None:
            raise RuntimeError(
                "Failed to create approval workflow."
            )

        return created

    # =========================================================
    # GET
    # =========================================================

    async def get_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Retrieve an approval workflow.
        """

        workflow = await self.workflow_repository.get_workflow(
            workflow_id
        )

        if workflow is None:
            raise ValueError(
                f"Approval workflow {workflow_id} was not found."
            )

        return workflow

    # =========================================================
    # DOCUMENT
    # =========================================================

    async def get_document_workflow(
        self,
        document_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Retrieve the workflow associated with a document.
        """

        workflow = (
            await self.workflow_repository.get_document_workflow(
                document_id
            )
        )

        if workflow is None:
            raise ValueError(
                f"No approval workflow exists for document "
                f"{document_id}."
            )

        return workflow

    # =========================================================
    # LIST
    # =========================================================

    async def list_organization_workflows(
        self,
        *,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ApprovalWorkflow]:
        """
        List workflows belonging to an organization.
        """

        if limit <= 0:
            raise ValueError(
                "Limit must be greater than zero."
            )

        if offset < 0:
            raise ValueError(
                "Offset cannot be negative."
            )

        return await self.workflow_repository.list_organization_workflows(
            org_id=org_id,
            limit=limit,
            offset=offset,
        )

    # =========================================================
    # STATUS
    # =========================================================

    async def update_status(
        self,
        *,
        workflow_id: UUID,
        status: ApprovalStatus,
    ) -> ApprovalWorkflow:
        """
        Update workflow status.

        ApprovalStatus is used here because this represents
        the state of the entire workflow.

        ApprovalDecision belongs to individual approval steps.
        """

        workflow = await self.get_workflow(workflow_id)

        self._validate_status_transition(
            current_status=workflow.status,
            new_status=status,
        )

        updated = await self.workflow_repository.update_status(
            workflow_id=workflow_id,
            status=status,
        )

        if updated is None:
            raise RuntimeError(
                f"Failed to update workflow {workflow_id}."
            )

        return updated

    # =========================================================
    # START REVIEW
    # =========================================================

    async def start_review(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Move a pending workflow into review.
        """

        workflow = await self.get_workflow(workflow_id)

        if workflow.status != ApprovalStatus.PENDING:
            raise ValueError(
                "Only pending workflows can enter review."
            )

        return await self.update_status(
            workflow_id=workflow_id,
            status=ApprovalStatus.IN_REVIEW,
        )

    # =========================================================
    # COMPLETE
    # =========================================================

    async def complete_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Mark a workflow as approved/completed.

        This should only happen after the approval engine has
        determined that all required approval steps are complete.
        """

        workflow = await self.get_workflow(workflow_id)

        if workflow.status not in (
            ApprovalStatus.PENDING,
            ApprovalStatus.IN_REVIEW,
        ):
            raise ValueError(
                "Only pending or in-review workflows "
                "can be completed."
            )

        has_pending = (
            await self.workflow_repository.has_pending_steps(
                workflow_id
            )
        )

        if has_pending:
            raise ValueError(
                "Workflow cannot be completed while pending "
                "approval steps remain."
            )

        completed = (
            await self.workflow_repository.complete_workflow(
                workflow_id
            )
        )

        if completed is None:
            raise RuntimeError(
                f"Failed to complete workflow {workflow_id}."
            )

        return completed

    # =========================================================
    # REJECT
    # =========================================================

    async def reject_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Mark a workflow as rejected.
        """

        workflow = await self.get_workflow(workflow_id)

        if workflow.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        ):
            raise ValueError(
                f"Workflow {workflow_id} is already closed."
            )

        rejected = (
            await self.workflow_repository.reject_workflow(
                workflow_id
            )
        )

        if rejected is None:
            raise RuntimeError(
                f"Failed to reject workflow {workflow_id}."
            )

        return rejected

    # =========================================================
    # CANCEL
    # =========================================================

    async def cancel_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Cancel an active approval workflow.
        """

        workflow = await self.get_workflow(workflow_id)

        if workflow.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        ):
            raise ValueError(
                "Closed workflows cannot be cancelled."
            )

        return await self.update_status(
            workflow_id=workflow_id,
            status=ApprovalStatus.CANCELLED,
        )

    # =========================================================
    # EXPIRE
    # =========================================================

    async def expire_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Mark an active workflow as expired.

        This is normally called by workers/background jobs.
        """

        workflow = await self.get_workflow(workflow_id)

        if workflow.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        ):
            raise ValueError(
                "Closed workflows cannot expire."
            )

        return await self.update_status(
            workflow_id=workflow_id,
            status=ApprovalStatus.EXPIRED,
        )

    # =========================================================
    # ESCALATE
    # =========================================================

    async def escalate_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Mark an active workflow as escalated.

        Individual step escalation is handled by step.py.
        This method handles workflow-level escalation.
        """

        workflow = await self.get_workflow(workflow_id)

        if workflow.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        ):
            raise ValueError(
                "Closed workflows cannot be escalated."
            )

        return await self.update_status(
            workflow_id=workflow_id,
            status=ApprovalStatus.ESCALATED,
        )

    # =========================================================
    # DELETE
    # =========================================================

    async def delete_workflow(
        self,
        workflow_id: UUID,
    ) -> bool:
        """
        Delete a workflow.

        In production, this should normally be restricted to
        administrative/system operations.
        """

        workflow = await self.get_workflow(workflow_id)

        if workflow.status in (
            ApprovalStatus.IN_REVIEW,
            ApprovalStatus.ESCALATED,
        ):
            raise ValueError(
                "Active workflows cannot be deleted."
            )

        return await self.workflow_repository.delete_workflow(
            workflow_id
        )

    # =========================================================
    # PENDING
    # =========================================================

    async def has_pending_steps(
        self,
        workflow_id: UUID,
    ) -> bool:
        """
        Check whether a workflow still has pending approval steps.
        """

        await self.get_workflow(workflow_id)

        return await self.workflow_repository.has_pending_steps(
            workflow_id
        )

    async def pending_step_count(
        self,
        workflow_id: UUID,
    ) -> int:
        """
        Return the number of pending steps.
        """

        await self.get_workflow(workflow_id)

        return await self.workflow_repository.pending_step_count(
            workflow_id
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _validate_status_transition(
        *,
        current_status: ApprovalStatus,
        new_status: ApprovalStatus,
    ) -> None:
        """
        Validate workflow-level state transitions.

        ApprovalStatus controls the lifecycle of the entire
        approval workflow.
        """

        if current_status == new_status:
            return

        allowed_transitions: dict[
            ApprovalStatus,
            set[ApprovalStatus],
        ] = {
            ApprovalStatus.PENDING: {
                ApprovalStatus.IN_REVIEW,
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.CANCELLED,
                ApprovalStatus.ESCALATED,
                ApprovalStatus.EXPIRED,
            },
            ApprovalStatus.IN_REVIEW: {
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.CANCELLED,
                ApprovalStatus.ESCALATED,
                ApprovalStatus.EXPIRED,
            },
            ApprovalStatus.ESCALATED: {
                ApprovalStatus.IN_REVIEW,
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.CANCELLED,
                ApprovalStatus.EXPIRED,
            },
            ApprovalStatus.APPROVED: set(),
            ApprovalStatus.REJECTED: set(),
            ApprovalStatus.CANCELLED: set(),
            ApprovalStatus.EXPIRED: set(),
        }

        allowed = allowed_transitions.get(
            current_status,
            set(),
        )

        if new_status not in allowed:
            raise ValueError(
                f"Invalid approval workflow transition: "
                f"{current_status.value} -> {new_status.value}"
            )