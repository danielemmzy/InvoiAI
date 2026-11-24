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
from app.services.audit_service import AuditService
from app.core.supabase import get_supabase


from app.core.db import execute

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
    - Write immutable approval history (approval_history) and, when
      an audit_service is supplied, the org-wide compliance audit
      trail (audit_logs) for every terminal decision.
    - Keep workflow state and step state consistent.

    Business rules live here.
    Repositories only handle persistence.
    """

    def __init__(
        self,
        workflow_repository: ApprovalWorkflowRepository,
        step_repository: ApprovalStepRepository,
        history_repository: ApprovalHistoryRepository,
        audit_service: AuditService | None = None,
    ) -> None:
        self.workflows = workflow_repository
        self.steps = step_repository
        self.history = history_repository
        self.audit_service = audit_service

    async def _audit(self, *, org_id: UUID, actor_id: UUID, action: str, resource_id: UUID, old_values: dict, new_values: dict) -> None:
        if self.audit_service is None:
            return
        try:
            await self.audit_service.log(
                org_id=org_id, user_id=actor_id, action=action,
                resource_type="approval_step", resource_id=resource_id,
                old_values=old_values, new_values=new_values,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to write audit_logs entry for %s", resource_id)

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

            if step.stage_number == 1:
                step.decision = ApprovalDecision.PENDING
            else:
                step.decision = ApprovalDecision.SKIPPED

        # One insert for every step instead of one per step.
        await self.steps.create_steps(steps)

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

        if step.stage_number != workflow.current_stage:
            raise ValueError(
                "The supplied step is not part of the current approval stage."
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
            await self._validate_industry_controls(workflow=workflow, step=step, actor_id=actor_id)

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

            await self._audit(
                org_id=workflow.org_id, actor_id=actor_id, action="document.approved",
                resource_id=step.id,
                old_values={"decision": ApprovalDecision.PENDING.value},
                new_values={"decision": ApprovalDecision.APPROVED.value, "comment": comment},
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

            await self._audit(
                org_id=workflow.org_id, actor_id=actor_id, action="document.rejected",
                resource_id=step.id,
                old_values={"decision": ApprovalDecision.PENDING.value},
                new_values={"decision": ApprovalDecision.REJECTED.value, "comment": comment},
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

    async def _validate_industry_controls(self, *, workflow: ApprovalWorkflow, step: ApprovalStep, actor_id: UUID) -> None:
        """Enforce SoD and monetary authority at the point of approval.

        Routing is advisory; the final decision is always checked against
        current authority and organization policy. Legacy installations that
        do not yet have the new tables fall back to the existing step limit.
        """
        db = get_supabase()
        try:
            doc_rows = (await execute((db.table("documents").select("id,created_by,ap_processed_by,currency,total_amount,vendor_name").eq("org_id", str(workflow.org_id)).eq("id", str(workflow.document_id)).limit(1))).data or [])
            doc = doc_rows[0] if doc_rows else {}
            sod_rows = (await execute((db.table("sod_rules").select("rule_key,enabled").eq("org_id", str(workflow.org_id)).eq("enabled", True))).data or [])
            sod = {r.get("rule_key") for r in sod_rows}

            # Approval is a decision on a specific document state. Material
            # changes after routing invalidate the pending decision rather than
            # allowing an approver to approve a different amount/vendor.
            current_amount = Decimal(str(doc.get("total_amount") or 0))
            if current_amount != Decimal(str(workflow.document_amount or 0)):
                raise ValueError("Invoice amount changed after approval routing. The approval workflow must be recalculated.")
            if workflow.vendor_name and str(doc.get("vendor_name") or "") != str(workflow.vendor_name):
                raise ValueError("Invoice vendor changed after approval routing. The approval workflow must be recalculated.")
            if str(doc.get("currency") or "").upper() != str(getattr(workflow, "metadata", {}).get("currency") or doc.get("currency") or "").upper():
                # Older workflows may not have a currency snapshot; only enforce
                # this when the workflow explicitly captured one.
                if getattr(workflow, "metadata", {}).get("currency"):
                    raise ValueError("Invoice currency changed after approval routing. The approval workflow must be recalculated.")

            if "no_self_approval" in sod and str(doc.get("created_by") or "") == str(actor_id):
                raise PermissionError("Segregation-of-duties policy prevents the requester from approving their own invoice.")
            if "processor_cannot_approve" in sod and str(doc.get("ap_processed_by") or "") == str(actor_id):
                raise PermissionError("Segregation-of-duties policy prevents the AP processor from approving the same invoice.")

            if workflow.workflow_type == "payment" and "separate_payment_authorizer" in sod:
                bill_workflows = (await execute((db.table("approval_workflows").select("id").eq("org_id", str(workflow.org_id)).eq("document_id", str(workflow.document_id)).eq("workflow_type", "bill"))).data or [])
                bill_ids = [str(x["id"]) for x in bill_workflows]
                if bill_ids:
                    prior_steps = (await execute((db.table("approval_steps").select("approver_id,claimed_by,decision").eq("org_id", str(workflow.org_id)).in_("workflow_id", bill_ids).eq("decision", "approved"))).data or [])
                    if any(str(x.get("approver_id") or "") == str(actor_id) or str(x.get("claimed_by") or "") == str(actor_id) for x in prior_steps):
                        raise PermissionError("Segregation-of-duties policy requires a different member to authorize payment than the invoice approver.")

            membership = (await execute((db.table("org_members").select("id").eq("org_id", str(workflow.org_id)).eq("user_id", str(actor_id)).eq("is_active", True).limit(1))).data or [])
            if membership:
                authorities = (await execute((db.table("approval_authorities").select("limit_amount,currency,effective_from,effective_until,is_active").eq("org_id", str(workflow.org_id)).eq("membership_id", membership[0]["id"]).eq("approval_type", "payment" if workflow.workflow_type == "payment" else "invoice").eq("is_active", True))).data or [])
                currency = str(doc.get("currency") or "").upper()
                amount = Decimal(str(doc.get("total_amount") or workflow.document_amount or 0))
                valid = False
                now = datetime.now(UTC)
                for authority in authorities:
                    if str(authority.get("currency") or "").upper() != currency: continue
                    start = authority.get("effective_from")
                    end = authority.get("effective_until")
                    if start and datetime.fromisoformat(str(start).replace("Z", "+00:00")) > now: continue
                    if end and datetime.fromisoformat(str(end).replace("Z", "+00:00")) < now: continue
                    if Decimal(str(authority.get("limit_amount") or 0)) >= amount:
                        valid = True
                        break
                if authorities and not valid:
                    raise PermissionError("The approver does not have sufficient current approval authority for this amount and currency.")
        except PermissionError:
            raise
        except Exception:
            # New controls are additive; do not break existing installations
            # before the migration has been applied.
            return

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
        Move the workflow to the next stage or complete it.

        A "stage" is one or more steps sharing stage_number that
        become active together:

        - sequential/any_one/group: exactly one step per stage.
          any_one differs only in that, when several steps are
          assigned to the same stage (e.g. any member of a set
          of individually-named approvers may act), the first
          decision resolves the stage and the rest are withdrawn
          (SKIPPED) rather than waited on.
        - parallel: every step in the stage must be APPROVED
          before the workflow advances; a single REJECTED already
          short-circuits the whole workflow in process_decision.
        """

        # The current stage, the next stage and the last-stage test all need
        # the same rows. One read of the workflow's steps replaces the three
        # separate reads this used to perform.
        all_steps = await self.steps.list_workflow_steps(workflow.id)
        stage_steps = sorted(
            (
                step
                for step in all_steps
                if step.stage_number == completed_step.stage_number
            ),
            key=lambda step: step.step_number,
        )

        if workflow.execution_mode == "parallel":
            still_pending = [
                s for s in stage_steps
                if s.id != completed_step.id and s.decision == ApprovalDecision.PENDING
            ]
            if still_pending:
                # Other approvers in this stage haven't decided yet —
                # record the approval but do not advance the workflow.
                return workflow

        elif workflow.execution_mode == "any_one":
            withdrawn = [
                sibling.id
                for sibling in stage_steps
                if sibling.id != completed_step.id and sibling.decision == ApprovalDecision.PENDING
            ]
            if withdrawn:
                # One statement instead of one round trip per sibling.
                await self.steps.update_steps(
                    withdrawn,
                    {"decision": ApprovalDecision.SKIPPED.value},
                    org_id=workflow.org_id,
                )

        is_last_stage = not any(s.stage_number > completed_step.stage_number for s in all_steps)

        if is_last_stage:
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

        next_stage_number = completed_step.stage_number + 1

        next_stage_steps = sorted(
            (
                step
                for step in all_steps
                if step.stage_number == next_stage_number
            ),
            key=lambda step: step.step_number,
        )

        if not next_stage_steps:
            raise RuntimeError(
                f"Approval stage {next_stage_number} does not exist."
            )

        for next_step in next_stage_steps:
            if next_step.decision != ApprovalDecision.SKIPPED:
                raise RuntimeError(
                    "Next approval step is not in an activatable state."
                )

        # Activate the whole stage with one statement rather than one per step.
        activated = await self.steps.update_steps(
            [next_step.id for next_step in next_stage_steps],
            {"decision": ApprovalDecision.PENDING.value},
            org_id=workflow.org_id,
        )

        if len(activated) != len(next_stage_steps):
            raise RuntimeError(
                "Failed to activate next approval step."
            )

        updated_workflow = await self.workflows.update_workflow(
            workflow.id,
            {
                "current_step": next_stage_steps[0].step_number,
                "current_stage": next_stage_number,
                "status": ApprovalStatus.IN_REVIEW.value,
            },
        )

        if updated_workflow is None:
            raise RuntimeError(
                "Failed to advance approval workflow."
            )

        await self._record_history(
            workflow_id=workflow.id,
            step_id=next_stage_steps[0].id,
            org_id=workflow.org_id,
            actor_id=actor_id,
            action="workflow_advanced",
            old_status=ApprovalStatus.IN_REVIEW,
            new_status=ApprovalStatus.IN_REVIEW,
            comment=None,
            metadata={
                "previous_stage": completed_step.stage_number,
                "current_stage": next_stage_number,
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

    async def _get_steps_by_stage(
        self,
        *,
        workflow_id: UUID,
        stage_number: int,
    ) -> list[ApprovalStep]:

        steps = await self.steps.list_workflow_steps(workflow_id)
        return sorted(
            (s for s in steps if s.stage_number == stage_number),
            key=lambda s: s.step_number,
        )

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

        if workflow.analysis_id is None and workflow.workflow_type != "payment":
            raise ValueError(
                "Approval workflow analysis_id is required for bill workflows."
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

            if step.approver_id is None and step.approver_group_id is None:
                raise ValueError(
                    "Approval step requires either approver_id or approver_group_id."
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
