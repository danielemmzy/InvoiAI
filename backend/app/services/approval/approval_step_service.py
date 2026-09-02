"""
============================================================
Approval Step Service

Application/service layer for approval steps.

Responsibilities:
- Create approval steps
- Retrieve steps
- List workflow steps
- Find current/pending steps
- Approve steps
- Reject steps
- Delegate steps
- Escalate steps
- Skip steps
- Send reminders
- Validate step transitions

No direct database queries.
No Supabase calls.
No HTTP/API logic.
No worker logic.

Workflow-level lifecycle belongs to workflow.py.
Step-level decisions belong here.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.core.enum.database import ApprovalDecision, OrgRole
from app.models.domain.approval import ApprovalHistory, ApprovalStep
from app.repositories.approval.step_repository import (
    ApprovalStepRepository,
)
from app.services.audit_service import AuditService
from app.services.approval.approval_history_service import ApprovalHistoryService
from uuid import uuid4


class ApprovalStepService:
    """
    Application service responsible for individual approval steps.
    """

    def __init__(
        self,
        step_repository: ApprovalStepRepository,
        audit_service: AuditService | None = None,
        approval_history_service: ApprovalHistoryService | None = None,
    ) -> None:
        self.step_repository = step_repository
        self.audit_service = audit_service
        self.approval_history_service = approval_history_service

    # =========================================================
    # CREATE
    # =========================================================

    async def create_step(
        self,
        *,
        workflow_id: UUID,
        org_id: UUID,
        step_number: int,
        step_name: str,
        approver_id: UUID,
        approver_role: OrgRole,
        spending_limit: Decimal | None = None,
        due_date: datetime | None = None,
    ) -> ApprovalStep:
        """
        Create an approval step.

        Every newly created step starts with PENDING decision.
        """

        if step_number <= 0:
            raise ValueError(
                "Step number must be greater than zero."
            )

        if not step_name.strip():
            raise ValueError(
                "Step name cannot be empty."
            )

        if spending_limit is not None and spending_limit < 0:
            raise ValueError(
                "Spending limit cannot be negative."
            )

        step = ApprovalStep(
            workflow_id=workflow_id,
            org_id=org_id,
            step_number=step_number,
            step_name=step_name,
            approver_id=approver_id,
            approver_role=approver_role,
            spending_limit=spending_limit,
            decision=ApprovalDecision.PENDING,
            decided_at=None,
            comment=None,
            delegated_to=None,
            delegated_at=None,
            delegation_reason=None,
            due_date=due_date,
            reminder_sent_at=None,
            escalated_at=None,
            created_at=datetime.now(UTC),
        )

        created = await self.step_repository.create_step(step)

        if created is None:
            raise RuntimeError(
                "Failed to create approval step."
            )

        return created

    # =========================================================
    # GET
    # =========================================================

    async def get_step(
        self,
        step_id: UUID,
    ) -> ApprovalStep:
        """
        Retrieve an approval step by ID.
        """

        step = await self.step_repository.get_step(step_id)

        if step is None:
            raise ValueError(
                f"Approval step {step_id} was not found."
            )

        return step

    # =========================================================
    # WORKFLOW STEPS
    # =========================================================

    async def list_workflow_steps(
        self,
        workflow_id: UUID,
    ) -> list[ApprovalStep]:
        """
        Return all steps belonging to a workflow.
        """

        return await self.step_repository.list_workflow_steps(
            workflow_id
        )

    # =========================================================
    # CURRENT STEP
    # =========================================================

    async def get_current_step(
        self,
        workflow_id: UUID,
    ) -> ApprovalStep:
        """
        Return the first pending step in the workflow.
        """

        step = await self.step_repository.get_current_step(
            workflow_id
        )

        if step is None:
            raise ValueError(
                f"Workflow {workflow_id} has no pending approval step."
            )

        return step

    # =========================================================
    # PENDING STEPS
    # =========================================================

    async def list_pending_steps(
        self,
        org_id: UUID,
    ) -> list[ApprovalStep]:
        """
        Return all pending approval steps for an organization.
        """

        return await self.step_repository.list_pending_steps(
            org_id
        )

    # =========================================================
    # APPROVER TASKS
    # =========================================================

    async def list_approver_tasks(
        self,
        approver_id: UUID,
    ) -> list[ApprovalStep]:
        """
        Return all pending steps assigned to an approver.
        """

        return await self.step_repository.list_approver_tasks(
            approver_id
        )

    # =========================================================
    # OVERDUE
    # =========================================================

    async def list_overdue_steps(
        self,
        org_id: UUID,
    ) -> list[ApprovalStep]:
        """
        Return pending steps whose due date has passed.
        """

        return await self.step_repository.list_overdue_steps(
            org_id
        )

    # =========================================================
    # APPROVE
    # =========================================================

    async def approve(
        self,
        *,
        step_id: UUID,
        approver_id: UUID,
        comment: str | None = None,
    ) -> ApprovalStep:
        """
        Approve an individual approval step.
        """

        step = await self.get_step(step_id)

        self._validate_approver(
            step=step,
            approver_id=approver_id,
        )

        self._ensure_pending(step)

        return await self._apply_decision(
            step=step,
            decision=ApprovalDecision.APPROVED,
            comment=comment,
            actor_id=approver_id,
        )

    # =========================================================
    # REJECT
    # =========================================================

    async def reject(
        self,
        *,
        step_id: UUID,
        approver_id: UUID,
        comment: str | None = None,
    ) -> ApprovalStep:
        """
        Reject an individual approval step.
        """

        step = await self.get_step(step_id)

        self._validate_approver(
            step=step,
            approver_id=approver_id,
        )

        self._ensure_pending(step)

        return await self._apply_decision(
            step=step,
            decision=ApprovalDecision.REJECTED,
            comment=comment,
            actor_id=approver_id,
        )

    # =========================================================
    # DELEGATE
    # =========================================================

    async def delegate(
        self,
        *,
        step_id: UUID,
        approver_id: UUID,
        delegated_to: UUID,
        reason: str,
    ) -> ApprovalStep:
        """
        Delegate an approval step to another user.

        Delegation is an actual ApprovalDecision state.
        """

        if approver_id == delegated_to:
            raise ValueError(
                "An approver cannot delegate a step to themselves."
            )

        if not reason.strip():
            raise ValueError(
                "Delegation reason is required."
            )

        step = await self.get_step(step_id)

        self._validate_approver(
            step=step,
            approver_id=approver_id,
        )

        self._ensure_pending(step)

        updated = await self.step_repository.delegate(
            step_id=step_id,
            delegated_to=delegated_to,
            reason=reason,
        )

        if updated is None:
            raise RuntimeError(
                f"Failed to delegate approval step {step_id}."
            )

        # The repository's existing delegate() only updates
        # delegated_to/delegated_at/reason. The decision itself
        # must also become DELEGATED.
        updated = await self.step_repository.update_step(
            step_id,
            {
                "decision": ApprovalDecision.DELEGATED.value,
            },
        )

        if updated is None:
            raise RuntimeError(
                f"Failed to mark approval step {step_id} as delegated."
            )

        return updated

    # =========================================================
    # ESCALATE
    # =========================================================

    async def escalate(
        self,
        *,
        step_id: UUID,
    ) -> ApprovalStep:
        """
        Escalate an individual approval step.
        """

        step = await self.get_step(step_id)

        self._ensure_pending(step)

        updated = await self.step_repository.update_step(
            step_id,
            {
                "decision": ApprovalDecision.ESCALATED.value,
                "escalated_at": datetime.now(UTC),
            },
        )

        if updated is None:
            raise RuntimeError(
                f"Failed to escalate approval step {step_id}."
            )

        return updated

    # =========================================================
    # SKIP
    # =========================================================

    async def skip(
        self,
        *,
        step_id: UUID,
        reason: str,
    ) -> ApprovalStep:
        """
        Skip an approval step.

        Skipping should normally be restricted to the approval
        engine/system or an authorized administrative operation.
        """

        if not reason.strip():
            raise ValueError(
                "A reason is required when skipping an approval step."
            )

        step = await self.get_step(step_id)

        self._ensure_pending(step)

        updated = await self.step_repository.update_step(
            step_id,
            {
                "decision": ApprovalDecision.SKIPPED.value,
                "decided_at": datetime.now(UTC),
                "comment": reason,
            },
        )

        if updated is None:
            raise RuntimeError(
                f"Failed to skip approval step {step_id}."
            )

        return updated

    # =========================================================
    # REMINDER
    # =========================================================

    async def send_reminder(
        self,
        step_id: UUID,
    ) -> ApprovalStep:
        """
        Mark a reminder as sent.

        Actual notification delivery belongs to a notification
        service/worker, not this service.
        """

        step = await self.get_step(step_id)

        self._ensure_pending(step)

        updated = await self.step_repository.send_reminder(
            step_id
        )

        if updated is None:
            raise RuntimeError(
                f"Failed to mark reminder for step {step_id}."
            )

        return updated

    # =========================================================
    # MARK ESCALATED
    # =========================================================

    async def mark_escalated(
        self,
        step_id: UUID,
    ) -> ApprovalStep:
        """
        Mark a pending step as escalated.
        """

        return await self.escalate(step_id=step_id)

    # =========================================================
    # DELETE
    # =========================================================

    async def delete_step(
        self,
        step_id: UUID,
    ) -> bool:
        """
        Delete an approval step.

        Active steps should not normally be deleted.
        """

        step = await self.get_step(step_id)

        if step.decision in (
            ApprovalDecision.PENDING,
            ApprovalDecision.ESCALATED,
        ):
            raise ValueError(
                "Pending or escalated approval steps cannot be deleted."
            )

        return await self.step_repository.delete_step(step_id)

    # =========================================================
    # HELPERS
    # =========================================================

    async def _apply_decision(
        self,
        *,
        step: ApprovalStep,
        decision: ApprovalDecision,
        comment: str | None,
        actor_id: UUID,
    ) -> ApprovalStep:
        """
        Apply a terminal decision to a pending step.

        Every decision now produces two immutable records:
          - approval_history: workflow-scoped, shown in the invoice's
            "history" tab.
          - audit_logs: org-wide compliance trail, shown in the audit
            log / used for investigations.

        Both writes happen after the decision is durably persisted, and
        neither failing rolls back the decision itself - a compliance
        record that failed to write is a problem to alert on, not a
        reason to tell an approver their approval didn't go through
        when it did. Failures are logged, not swallowed silently.
        """

        old_status = step.decision

        updated = await self.step_repository.update_decision(
            step_id=step.id,
            decision=decision,
            comment=comment,
        )

        if updated is None:
            raise RuntimeError(
                f"Failed to apply decision to approval step {step.id}."
            )

        action = "document.approved" if decision == ApprovalDecision.APPROVED else "document.rejected"

        if self.approval_history_service is not None:
            try:
                await self.approval_history_service.create_history(
                    ApprovalHistory(
                        id=uuid4(),
                        workflow_id=step.workflow_id,
                        step_id=step.id,
                        org_id=step.org_id,
                        actor_id=actor_id,
                        action=action,
                        comment=comment,
                        old_status=old_status,
                        new_status=decision,
                        metadata={},
                        created_at=datetime.now(UTC),
                    )
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    "Failed to write approval_history for step %s", step.id
                )

        if self.audit_service is not None:
            try:
                await self.audit_service.log(
                    org_id=step.org_id,
                    user_id=actor_id,
                    action=action,
                    resource_type="approval_step",
                    resource_id=step.id,
                    old_values={"decision": old_status.value if hasattr(old_status, "value") else str(old_status)},
                    new_values={"decision": decision.value if hasattr(decision, "value") else str(decision), "comment": comment},
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    "Failed to write audit_logs entry for step %s", step.id
                )

        return updated

    @staticmethod
    def _ensure_pending(
        step: ApprovalStep,
    ) -> None:
        """
        Only pending steps can receive a normal decision.
        """

        if step.decision != ApprovalDecision.PENDING:
            raise ValueError(
                f"Approval step {step.id} is already "
                f"{step.decision.value}."
            )

    @staticmethod
    def _validate_approver(
        *,
        step: ApprovalStep,
        approver_id: UUID,
    ) -> None:
        """
        Ensure the acting user is the assigned approver.

        Delegated approval authorization can be expanded later
        when delegated ownership is represented explicitly.
        """

        if step.approver_id != approver_id:
            raise PermissionError(
                "User is not authorized to act on this approval step."
            )

    # =========================================================
    # STATE CHECKS
    # =========================================================

    async def step_exists(
        self,
        step_id: UUID,
    ) -> bool:
        """
        Check whether an approval step exists.
        """

        return await self.step_repository.step_exists(step_id)

    async def pending_count(
        self,
        workflow_id: UUID,
    ) -> int:
        """
        Return the number of pending steps in a workflow.
        """

        return await self.step_repository.pending_count(
            workflow_id
        )