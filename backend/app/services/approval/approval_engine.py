# app/services/approval_engine.py

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.enum.application import ApprovalStatus
from app.core.enum.database import ApprovalDecision
from app.models.domain.approval import (
    ApprovalHistory,
    ApprovalStep,
    ApprovalWorkflow,
)
from app.repositories.approval.history_repository import ApprovalHistoryRepository
from app.repositories.approval.step_repository import ApprovalStepRepository
from app.repositories.approval.workflow_repository import ApprovalWorkflowRepository


class ApprovalEngine:
    """
    Core approval workflow engine.

    Responsibilities:
    - Start approval workflows.
    - Process approval-step decisions.
    - Advance workflows.
    - Complete/reject workflows.
    - Handle delegation.
    - Handle escalation.
    - Write immutable approval history.
    - Keep workflow state and step state consistent.

    Business rules live here.
    Repositories only handle persistence.
    """

    def __init__(
        self,
        workflow_repository: ApprovalWorkflowRepository,
        step_repository: ApprovalStepRepository,
        history_repository: ApprovalHistoryRepository,
    ) -> None:
        self.workflows = workflow_repository
        self.steps = step_repository
        self.history = history_repository

    # =========================================================
    # START WORKFLOW
    # =========================================================

    async def start_workflow(
        self,
        *,
        workflow: ApprovalWorkflow,
        steps: list[ApprovalStep],
    ) -> ApprovalWorkflow:
        """
        Create a workflow and its approval steps.

        The first step must always be pending.
        Every step must belong to the same workflow/org.
        """

        self._validate_workflow(workflow)
        self._validate_steps(workflow, steps)

        if not steps:
            raise ValueError(
                "Approval workflow must contain at least one step."
            )

        workflow.total_steps = len(steps)
        workflow.current_step = 1
        workflow.status = ApprovalStatus.IN_REVIEW

        created_workflow = await self.workflows.create_workflow(workflow)

        if created_workflow is None:
            raise RuntimeError(
                "Failed to create approval workflow."
            )

        for step in steps:
            step.workflow_id = created_workflow.id
            step.org_id = created_workflow.org_id

            if step.step_number == 1:
                step.decision = ApprovalDecision.PENDING
            else:
                step.decision = ApprovalDecision.SKIPPED

            created_step = await self.steps.create_step(step)

            if created_step is None:
                raise RuntimeError(
                    f"Failed to create approval step "
                    f"{step.step_number}."
                )

        await self._record_history(
            workflow_id=created_workflow.id,
            step_id=steps[0].id,
            org_id=created_workflow.org_id,
            actor_id=created_workflow.initiated_by,
            action="workflow_started",
            old_status=ApprovalStatus.PENDING,
            new_status=ApprovalStatus.IN_REVIEW,
            comment=None,
            metadata={
                "total_steps": created_workflow.total_steps,
            },
        )

        return created_workflow

    # =========================================================
    # PROCESS DECISION
    # =========================================================

    async def process_decision(
        self,
        *,
        workflow_id: UUID,
        step_id: UUID,
        actor_id: UUID,
        decision: ApprovalDecision,
        comment: str | None = None,
        delegated_to: UUID | None = None,
        delegation_reason: str | None = None,
    ) -> ApprovalWorkflow:
        """
        Process a decision against the current approval step.
        """

        workflow = await self.workflows.get_workflow(workflow_id)

        if workflow is None:
            raise ValueError("Approval workflow not found.")

        step = await self.steps.get_step(step_id)

        if step is None:
            raise ValueError("Approval step not found.")

        self._validate_step_belongs_to_workflow(
            workflow,
            step,
        )

        self._validate_actor(
            actor_id=actor_id,
            step=step,
        )

        if step.step_number != workflow.current_step:
            raise ValueError(
                "The supplied step is not the current approval step."
            )

        if step.decision != ApprovalDecision.PENDING:
            raise ValueError(
                "This approval step has already been decided."
            )

        self._validate_decision(
            decision=decision,
            delegated_to=delegated_to,
            delegation_reason=delegation_reason,
        )

        old_status = workflow.status

        if decision == ApprovalDecision.APPROVED:
            await self.steps.approve(
                step_id,
                comment,
            )

            await self._record_history(
                workflow_id=workflow.id,
                step_id=step.id,
                org_id=workflow.org_id,
                actor_id=actor_id,
                action="step_approved",
                old_status=old_status,
                new_status=old_status,
                comment=comment,
                metadata={},
            )

            return await self._advance_after_approval(
                workflow=workflow,
                completed_step=step,
                actor_id=actor_id,
            )

        if decision == ApprovalDecision.REJECTED:
            await self.steps.reject(
                step_id,
                comment,
            )

            rejected = await self.workflows.reject_workflow(
                workflow.id,
            )

            if rejected is None:
                raise RuntimeError(
                    "Failed to reject approval workflow."
                )

            await self._record_history(
                workflow_id=workflow.id,
                step_id=step.id,
                org_id=workflow.org_id,
                actor_id=actor_id,
                action="workflow_rejected",
                old_status=old_status,
                new_status=ApprovalStatus.REJECTED,
                comment=comment,
                metadata={},
            )

            return rejected

        if decision == ApprovalDecision.DELEGATED:
            await self.steps.delegate(
                step_id=step.id,
                delegated_to=delegated_to,
                reason=delegation_reason,
            )

            await self._record_history(
                workflow_id=workflow.id,
                step_id=step.id,
                org_id=workflow.org_id,
                actor_id=actor_id,
                action="step_delegated",
                old_status=old_status,
                new_status=old_status,
                comment=comment,
                metadata={
                    "delegated_to": str(delegated_to),
                    "delegation_reason": delegation_reason,
                },
            )

            updated = await self.workflows.get_workflow(
                workflow.id,
            )

            if updated is None:
                raise RuntimeError(
                    "Workflow disappeared after delegation."
                )

            return updated

        if decision == ApprovalDecision.ESCALATED:
            await self.steps.mark_escalated(step.id)

            updated = await self.workflows.update_status(
                workflow.id,
                ApprovalStatus.ESCALATED,
            )

            if updated is None:
                raise RuntimeError(
                    "Failed to escalate approval workflow."
                )

            await self._record_history(
                workflow_id=workflow.id,
                step_id=step.id,
                org_id=workflow.org_id,
                actor_id=actor_id,
                action="step_escalated",
                old_status=old_status,
                new_status=ApprovalStatus.ESCALATED,
                comment=comment,
                metadata={},
            )

            return updated

        if decision == ApprovalDecision.SKIPPED:
            raise ValueError(
                "An approver cannot manually skip the current step."
            )

        if decision == ApprovalDecision.PENDING:
            raise ValueError(
                "A pending decision cannot be submitted."
            )

        raise ValueError(
            f"Unsupported approval decision: {decision}"
        )

    # =========================================================
    # ADVANCE WORKFLOW
    # =========================================================

    async def _advance_after_approval(
        self,
        *,
        workflow: ApprovalWorkflow,
        completed_step: ApprovalStep,
        actor_id: UUID,
    ) -> ApprovalWorkflow:
        """
        Move the workflow to the next step or complete it.
        """

        if completed_step.step_number >= workflow.total_steps:
            completed = await self.workflows.complete_workflow(
                workflow.id,
            )

            if completed is None:
                raise RuntimeError(
                    "Failed to complete approval workflow."
                )

            await self._record_history(
                workflow_id=workflow.id,
                step_id=completed_step.id,
                org_id=workflow.org_id,
                actor_id=actor_id,
                action="workflow_completed",
                old_status=ApprovalStatus.IN_REVIEW,
                new_status=ApprovalStatus.APPROVED,
                comment=None,
                metadata={
                    "completed_step": completed_step.step_number,
                },
            )

            return completed

        next_step_number = completed_step.step_number + 1

        next_step = await self._get_step_by_number(
            workflow_id=workflow.id,
            step_number=next_step_number,
        )

        if next_step is None:
            raise RuntimeError(
                f"Approval step {next_step_number} "
                "does not exist."
            )

        if next_step.decision != ApprovalDecision.SKIPPED:
            raise RuntimeError(
                "Next approval step is not in an activatable state."
            )

        updated_step = await self.steps.update_step(
            next_step.id,
            {
                "decision": ApprovalDecision.PENDING.value,
            },
        )

        if updated_step is None:
            raise RuntimeError(
                "Failed to activate next approval step."
            )

        updated_workflow = await self.workflows.update_workflow(
            workflow.id,
            {
                "current_step": next_step_number,
                "status": ApprovalStatus.IN_REVIEW.value,
            },
        )

        if updated_workflow is None:
            raise RuntimeError(
                "Failed to advance approval workflow."
            )

        await self._record_history(
            workflow_id=workflow.id,
            step_id=next_step.id,
            org_id=workflow.org_id,
            actor_id=actor_id,
            action="workflow_advanced",
            old_status=ApprovalStatus.IN_REVIEW,
            new_status=ApprovalStatus.IN_REVIEW,
            comment=None,
            metadata={
                "previous_step": completed_step.step_number,
                "current_step": next_step_number,
            },
        )

        return updated_workflow

    # =========================================================
    # ESCALATION
    # =========================================================

    async def escalate_workflow(
        self,
        *,
        workflow_id: UUID,
        step_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> ApprovalWorkflow:
        """
        Explicitly escalate a workflow.
        """

        if not reason.strip():
            raise ValueError(
                "Escalation reason is required."
            )

        workflow = await self.workflows.get_workflow(workflow_id)

        if workflow is None:
            raise ValueError("Approval workflow not found.")

        step = await self.steps.get_step(step_id)

        if step is None:
            raise ValueError("Approval step not found.")

        self._validate_step_belongs_to_workflow(
            workflow,
            step,
        )

        if step.decision != ApprovalDecision.PENDING:
            raise ValueError(
                "Only pending approval steps can be escalated."
            )

        await self.steps.mark_escalated(step.id)

        updated = await self.workflows.update_status(
            workflow.id,
            ApprovalStatus.ESCALATED,
        )

        if updated is None:
            raise RuntimeError(
                "Failed to update workflow escalation status."
            )

        await self._record_history(
            workflow_id=workflow.id,
            step_id=step.id,
            org_id=workflow.org_id,
            actor_id=actor_id,
            action="workflow_escalated",
            old_status=workflow.status,
            new_status=ApprovalStatus.ESCALATED,
            comment=reason,
            metadata={
                "reason": reason,
            },
        )

        return updated

    # =========================================================
    # DELEGATION
    # =========================================================

    async def delegate_step(
        self,
        *,
        workflow_id: UUID,
        step_id: UUID,
        actor_id: UUID,
        delegated_to: UUID,
        reason: str,
    ) -> ApprovalWorkflow:
        """
        Delegate an approval step to another approver.
        """

        if not reason.strip():
            raise ValueError(
                "Delegation reason is required."
            )

        if actor_id == delegated_to:
            raise ValueError(
                "An approval step cannot be delegated to itself."
            )

        workflow = await self.workflows.get_workflow(workflow_id)

        if workflow is None:
            raise ValueError("Approval workflow not found.")

        step = await self.steps.get_step(step_id)

        if step is None:
            raise ValueError("Approval step not found.")

        self._validate_step_belongs_to_workflow(
            workflow,
            step,
        )

        self._validate_actor(
            actor_id=actor_id,
            step=step,
        )

        if step.decision != ApprovalDecision.PENDING:
            raise ValueError(
                "Only pending steps can be delegated."
            )

        delegated = await self.steps.delegate(
            step_id=step.id,
            delegated_to=delegated_to,
            reason=reason,
        )

        if delegated is None:
            raise RuntimeError(
                "Failed to delegate approval step."
            )

        await self._record_history(
            workflow_id=workflow.id,
            step_id=step.id,
            org_id=workflow.org_id,
            actor_id=actor_id,
            action="step_delegated",
            old_status=workflow.status,
            new_status=workflow.status,
            comment=reason,
            metadata={
                "delegated_to": str(delegated_to),
                "delegation_reason": reason,
            },
        )

        refreshed = await self.workflows.get_workflow(
            workflow.id,
        )

        if refreshed is None:
            raise RuntimeError(
                "Workflow disappeared after delegation."
            )

        return refreshed

    # =========================================================
    # OVERDUE PROCESSING
    # =========================================================

    async def escalate_overdue_steps(
        self,
        *,
        org_id: UUID,
        actor_id: UUID,
    ) -> int:
        """
        Escalate all overdue pending steps for an organization.

        Returns number of escalated steps.
        """

        overdue_steps = await self.steps.list_overdue_steps(
            org_id,
        )

        escalated_count = 0

        for step in overdue_steps:
            workflow = await self.workflows.get_workflow(
                step.workflow_id,
            )

            if workflow is None:
                continue

            if workflow.status in {
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.CANCELLED,
                ApprovalStatus.EXPIRED,
            }:
                continue

            await self.steps.mark_escalated(step.id)

            updated = await self.workflows.update_status(
                workflow.id,
                ApprovalStatus.ESCALATED,
            )

            if updated is None:
                continue

            await self._record_history(
                workflow_id=workflow.id,
                step_id=step.id,
                org_id=workflow.org_id,
                actor_id=actor_id,
                action="step_auto_escalated",
                old_status=workflow.status,
                new_status=ApprovalStatus.ESCALATED,
                comment="Approval step exceeded its due date.",
                metadata={
                    "due_date": (
                        step.due_date.isoformat()
                        if step.due_date
                        else None
                    ),
                },
            )

            escalated_count += 1

        return escalated_count

    # =========================================================
    # REMINDERS
    # =========================================================

    async def send_step_reminder(
        self,
        *,
        workflow_id: UUID,
        step_id: UUID,
        actor_id: UUID,
    ) -> ApprovalStep:
        """
        Record that an approval reminder was sent.
        """

        workflow = await self.workflows.get_workflow(
            workflow_id,
        )

        if workflow is None:
            raise ValueError("Approval workflow not found.")

        step = await self.steps.get_step(step_id)

        if step is None:
            raise ValueError("Approval step not found.")

        self._validate_step_belongs_to_workflow(
            workflow,
            step,
        )

        if step.decision != ApprovalDecision.PENDING:
            raise ValueError(
                "Cannot remind a completed approval step."
            )

        updated = await self.steps.send_reminder(
            step.id,
        )

        if updated is None:
            raise RuntimeError(
                "Failed to record approval reminder."
            )

        await self._record_history(
            workflow_id=workflow.id,
            step_id=step.id,
            org_id=workflow.org_id,
            actor_id=actor_id,
            action="reminder_sent",
            old_status=workflow.status,
            new_status=workflow.status,
            comment=None,
            metadata={},
        )

        return updated

    # =========================================================
    # AUTO APPROVAL / REJECTION
    # =========================================================

    async def auto_approve(
        self,
        *,
        workflow_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> ApprovalWorkflow:
        """
        Automatically approve an entire workflow.
        """

        workflow = await self.workflows.get_workflow(
            workflow_id,
        )

        if workflow is None:
            raise ValueError("Approval workflow not found.")

        if workflow.auto_rejected:
            raise ValueError(
                "A workflow marked auto-rejected cannot be auto-approved."
            )

        if workflow.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        }:
            raise ValueError(
                "Workflow has already reached a terminal state."
            )

        updated = await self.workflows.update_workflow(
            workflow.id,
            {
                "status": ApprovalStatus.APPROVED.value,
                "auto_approved": True,
                "completed_at": datetime.now(UTC),
            },
        )

        if updated is None:
            raise RuntimeError(
                "Failed to auto-approve workflow."
            )

        await self._record_history(
            workflow_id=workflow.id,
            step_id=workflow.id,
            org_id=workflow.org_id,
            actor_id=actor_id,
            action="workflow_auto_approved",
            old_status=workflow.status,
            new_status=ApprovalStatus.APPROVED,
            comment=reason,
            metadata={
                "automatic": True,
                "reason": reason,
            },
        )

        return updated

    async def auto_reject(
        self,
        *,
        workflow_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> ApprovalWorkflow:
        """
        Automatically reject an entire workflow.
        """

        if not reason.strip():
            raise ValueError(
                "Auto-rejection reason is required."
            )

        workflow = await self.workflows.get_workflow(
            workflow_id,
        )

        if workflow is None:
            raise ValueError("Approval workflow not found.")

        if workflow.auto_approved:
            raise ValueError(
                "A workflow marked auto-approved cannot be auto-rejected."
            )

        if workflow.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        }:
            raise ValueError(
                "Workflow has already reached a terminal state."
            )

        updated = await self.workflows.update_workflow(
            workflow.id,
            {
                "status": ApprovalStatus.REJECTED.value,
                "auto_rejected": True,
                "completed_at": datetime.now(UTC),
            },
        )

        if updated is None:
            raise RuntimeError(
                "Failed to auto-reject workflow."
            )

        await self._record_history(
            workflow_id=workflow.id,
            step_id=workflow.id,
            org_id=workflow.org_id,
            actor_id=actor_id,
            action="workflow_auto_rejected",
            old_status=workflow.status,
            new_status=ApprovalStatus.REJECTED,
            comment=reason,
            metadata={
                "automatic": True,
                "reason": reason,
            },
        )

        return updated

    # =========================================================
    # HISTORY
    # =========================================================

    async def _record_history(
        self,
        *,
        workflow_id: UUID,
        step_id: UUID,
        org_id: UUID,
        actor_id: UUID,
        action: str,
        old_status: ApprovalStatus,
        new_status: ApprovalStatus,
        comment: str | None,
        metadata: dict[str, Any],
    ) -> ApprovalHistory:
        """
        Write an immutable audit event.
        """

        history = ApprovalHistory(
            id=UUID(int=0),
            workflow_id=workflow_id,
            step_id=step_id,
            org_id=org_id,
            actor_id=actor_id,
            action=action,
            comment=comment,
            old_status=old_status,
            new_status=new_status,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )

        created = await self.history.create_history(
            history,
        )

        if created is None:
            raise RuntimeError(
                "Failed to create approval history."
            )

        return created

    # =========================================================
    # INTERNAL QUERIES
    # =========================================================

    async def _get_step_by_number(
        self,
        *,
        workflow_id: UUID,
        step_number: int,
    ) -> ApprovalStep | None:

        steps = await self.steps.list_workflow_steps(
            workflow_id,
        )

        for step in steps:
            if step.step_number == step_number:
                return step

        return None

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _validate_workflow(
        workflow: ApprovalWorkflow,
    ) -> None:

        if workflow.id is None:
            raise ValueError(
                "Approval workflow id is required."
            )

        if workflow.org_id is None:
            raise ValueError(
                "Approval workflow org_id is required."
            )

        if workflow.document_id is None:
            raise ValueError(
                "Approval workflow document_id is required."
            )

        if workflow.analysis_id is None:
            raise ValueError(
                "Approval workflow analysis_id is required."
            )

        if workflow.initiated_by is None:
            raise ValueError(
                "Approval workflow initiated_by is required."
            )

        if workflow.total_steps < 1:
            raise ValueError(
                "Approval workflow must have at least one step."
            )

        if workflow.document_amount < Decimal("0"):
            raise ValueError(
                "Document amount cannot be negative."
            )

    @staticmethod
    def _validate_steps(
        workflow: ApprovalWorkflow,
        steps: list[ApprovalStep],
    ) -> None:

        numbers = sorted(
            step.step_number
            for step in steps
        )

        expected = list(
            range(
                1,
                len(steps) + 1,
            )
        )

        if numbers != expected:
            raise ValueError(
                "Approval steps must be numbered consecutively "
                "starting from 1."
            )

        for step in steps:
            if step.id is None:
                raise ValueError(
                    "Approval step id is required."
                )

            if step.approver_id is None:
                raise ValueError(
                    "Approval step approver_id is required."
                )

            if step.workflow_id not in {
                workflow.id,
                None,
            }:
                raise ValueError(
                    "Approval step belongs to another workflow."
                )

            if step.org_id not in {
                workflow.org_id,
                None,
            }:
                raise ValueError(
                    "Approval step belongs to another organization."
                )

    @staticmethod
    def _validate_step_belongs_to_workflow(
        workflow: ApprovalWorkflow,
        step: ApprovalStep,
    ) -> None:

        if step.workflow_id != workflow.id:
            raise ValueError(
                "Approval step does not belong to workflow."
            )

        if step.org_id != workflow.org_id:
            raise ValueError(
                "Approval step does not belong to workflow organization."
            )

    @staticmethod
    def _validate_actor(
        *,
        actor_id: UUID,
        step: ApprovalStep,
    ) -> None:

        valid_approvers = {
            step.approver_id,
            step.delegated_to,
        }

        if actor_id not in valid_approvers:
            raise PermissionError(
                "Actor is not authorized to act on this approval step."
            )

    @staticmethod
    def _validate_decision(
        *,
        decision: ApprovalDecision,
        delegated_to: UUID | None,
        delegation_reason: str | None,
    ) -> None:

        if decision == ApprovalDecision.DELEGATED:
            if delegated_to is None:
                raise ValueError(
                    "delegated_to is required for delegation."
                )

            if not delegation_reason:
                raise ValueError(
                    "delegation_reason is required for delegation."
                )

        elif delegated_to is not None:
            raise ValueError(
                "delegated_to can only be supplied for delegation."
            )