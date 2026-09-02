
"""
============================================================
Approval Worker

Background processing for approval workflows.

Responsibilities:
- Process approval workflow events asynchronously.
- Advance workflows after decisions.
- Handle automatic approval/rejection rules.
- Create approval history events through the service layer.
- Handle overdue and escalation processing.
- Keep business orchestration out of repositories.
- Keep direct database access out of the worker.

The worker should be invoked by a task runner such as:
- Celery
- ARQ
- Dramatiq
- RQ
- FastAPI BackgroundTasks for lightweight workloads

Production recommendation:
Use a durable queue such as Celery/Redis or ARQ/Redis for
approval processing that must survive application restarts.
============================================================
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import ApprovalDecision
from app.core.enum.application import ApprovalStatus
from app.models.domain.approval import ApprovalWorkflow
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class ApprovalWorker(BaseWorker):
    """
    Background worker for approval workflow processing.

    The worker is intentionally thin.

    It coordinates services rather than implementing database
    persistence directly.
    """

    def __init__(
        self,
        approval_engine,
        workflow_service,
        step_service,
        history_service,
    ) -> None:
        super().__init__()
        self.approval_engine = approval_engine
        self.workflow_service = workflow_service
        self.step_service = step_service
        self.history_service = history_service

    async def run(self, *, workflow_id: UUID) -> None:
        await self.process_workflow(workflow_id)

    # ========================================================
    # Workflow Processing
    # ========================================================

    async def process_workflow(
        self,
        workflow_id: UUID,
    ) -> None:
        """
        Process a single approval workflow.

        This is the main worker entry point.
        """

        logger.info(
            "Processing approval workflow",
            extra={
                "workflow_id": str(workflow_id),
            },
        )

        workflow = await self.workflow_service.get_workflow(workflow_id)

        if workflow is None:
            logger.warning(
                "Approval workflow not found",
                extra={"workflow_id": str(workflow_id)},
            )
            return

        if self._is_terminal(workflow.status):
            logger.info(
                "Approval workflow already terminal",
                extra={
                    "workflow_id": str(workflow_id),
                    "status": workflow.status.value,
                },
            )
            return

        await self._process_workflow(workflow)

    async def _process_workflow(
        self,
        workflow: ApprovalWorkflow,
    ) -> None:
        """
        Execute the workflow processing pipeline.
        """

        # ----------------------------------------------------
        # 1. Check automatic decision rules
        # ----------------------------------------------------

        automatic_decision = await self._evaluate_automatic_decision(
            workflow
        )

        if automatic_decision is not None:
            await self._apply_automatic_decision(
                workflow,
                automatic_decision,
            )
            return

        # ----------------------------------------------------
        # 2. Get current approval step
        # ----------------------------------------------------

        current_step = await self.step_service.get_current_step(
            workflow.id
        )

        if current_step is None:
            await self._complete_if_no_pending_steps(workflow)
            return

        # ----------------------------------------------------
        # 3. Check expiration / overdue state
        # ----------------------------------------------------

        if self._is_overdue(current_step.due_date):
            await self._handle_overdue_step(
                workflow,
                current_step,
            )
            return

        # ----------------------------------------------------
        # 4. Nothing else to process
        # ----------------------------------------------------

        logger.debug(
            "Approval workflow waiting for decision",
            extra={
                "workflow_id": str(workflow.id),
                "step_id": str(current_step.id),
                "step_number": current_step.step_number,
            },
        )

    # ========================================================
    # Automatic Decisions
    # ========================================================

    async def _evaluate_automatic_decision(
        self,
        workflow: ApprovalWorkflow,
    ) -> ApprovalDecision | None:
        """
        Ask the approval engine whether the workflow qualifies
        for an automatic decision.

        The engine owns the business rules.
        """

        decision = await self.approval_engine.evaluate(
            workflow
        )

        if decision in (
            ApprovalDecision.APPROVED,
            ApprovalDecision.REJECTED,
        ):
            return decision

        return None

    async def _apply_automatic_decision(
        self,
        workflow: ApprovalWorkflow,
        decision: ApprovalDecision,
    ) -> None:
        """
        Apply an automatic approval/rejection.
        """

        logger.info(
            "Applying automatic approval decision",
            extra={
                "workflow_id": str(workflow.id),
                "decision": decision.value,
            },
        )

        if decision == ApprovalDecision.APPROVED:
            updated = await self.workflow_service.complete_workflow(
                workflow.id,
                automatic=True,
            )

        elif decision == ApprovalDecision.REJECTED:
            updated = await self.workflow_service.reject_workflow(
                workflow.id,
                automatic=True,
            )

        else:
            return

        if updated is None:
            raise RuntimeError(
                f"Unable to update workflow {workflow.id}"
            )

        await self.history_service.record_event(
            workflow_id=workflow.id,
            step_id=None,
            actor_id=workflow.initiated_by,
            action=f"automatic_{decision.value}",
            old_status=workflow.status,
            new_status=updated.status,
            comment=None,
            metadata={
                "automatic": True,
                "decision": decision.value,
            },
        )

    # ========================================================
    # Step Processing
    # ========================================================

    async def _complete_if_no_pending_steps(
        self,
        workflow: ApprovalWorkflow,
    ) -> None:
        """
        Complete a workflow when no pending approval steps remain.
        """

        logger.info(
            "No pending approval steps remain",
            extra={
                "workflow_id": str(workflow.id),
            },
        )

        updated = await self.workflow_service.complete_workflow(
            workflow.id
        )

        if updated is None:
            raise RuntimeError(
                f"Unable to complete workflow {workflow.id}"
            )

        await self.history_service.record_event(
            workflow_id=workflow.id,
            step_id=None,
            actor_id=workflow.initiated_by,
            action="workflow_completed",
            old_status=workflow.status,
            new_status=updated.status,
            comment=None,
            metadata={
                "reason": "no_pending_steps",
            },
        )

    async def _handle_overdue_step(
        self,
        workflow: ApprovalWorkflow,
        step,
    ) -> None:
        """
        Process an overdue approval step.

        Escalation policy belongs to the approval engine/service,
        not the worker.
        """

        logger.info(
            "Approval step is overdue",
            extra={
                "workflow_id": str(workflow.id),
                "step_id": str(step.id),
                "step_number": step.step_number,
            },
        )

        await self.step_service.mark_escalated(
            step.id
        )

        updated = await self.workflow_service.update_status(
            workflow.id,
            ApprovalStatus.ESCALATED,
        )

        if updated is None:
            raise RuntimeError(
                f"Unable to escalate workflow {workflow.id}"
            )

        await self.history_service.record_event(
            workflow_id=workflow.id,
            step_id=step.id,
            actor_id=step.approver_id,
            action="step_escalated",
            old_status=workflow.status,
            new_status=updated.status,
            comment=None,
            metadata={
                "reason": "step_overdue",
                "step_number": step.step_number,
            },
        )

    # ========================================================
    # Scheduled Processing
    # ========================================================

    async def process_pending_workflows(
        self,
        org_id: UUID,
        limit: int = 100,
    ) -> int:
        """
        Process a batch of pending workflows.

        Returns the number of workflows submitted for processing.
        """

        workflows = await self.workflow_service.list_pending_workflows(
            org_id=org_id,
            limit=limit,
        )

        processed = 0

        for workflow in workflows:
            try:
                await self.process_workflow(
                    workflow.id
                )
                processed += 1

            except Exception:
                logger.exception(
                    "Failed processing workflow in batch",
                    extra={
                        "workflow_id": str(workflow.id),
                        "org_id": str(org_id),
                    },
                )

        return processed

    async def process_overdue_workflows(
        self,
        org_id: UUID,
        limit: int = 100,
    ) -> int:
        """
        Process workflows containing overdue approval steps.
        """

        workflows = (
            await self.workflow_service.list_overdue_workflows(
                org_id=org_id,
                limit=limit,
            )
        )

        processed = 0

        for workflow in workflows:
            try:
                await self.process_workflow(
                    workflow.id
                )
                processed += 1

            except Exception:
                logger.exception(
                    "Failed processing overdue workflow",
                    extra={
                        "workflow_id": str(workflow.id),
                        "org_id": str(org_id),
                    },
                )

        return processed

    # ========================================================
    # Validation Helpers
    # ========================================================

    @staticmethod
    def _is_terminal(
        status: ApprovalStatus,
    ) -> bool:
        """
        Determine whether a workflow can no longer progress.
        """

        return status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        )

    @staticmethod
    def _is_overdue(
        due_date: datetime | None,
    ) -> bool:
        """
        Check whether a step is overdue.
        """

        if due_date is None:
            return False

        now = datetime.now(UTC)

        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=UTC)

        return due_date < now
