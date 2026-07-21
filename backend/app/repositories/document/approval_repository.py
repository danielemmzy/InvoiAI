"""
============================================================
Approval Repository

Persistence layer for approval workflows.

Owns:
- approval_workflows
- approval_steps
- approval_history

Read-only views:
- approval_queue
- pending_approvals

No business logic.
No authorization.
============================================================
"""

from datetime import UTC, datetime
from typing import Any

from backend.app.core.enum.enums import (
    ApprovalDecision,
    ApprovalStatus,
)
from app.repositories.base import BaseRepository


class ApprovalRepository(BaseRepository):
    """
    Repository for approval workflows.
    """

    WORKFLOW_TABLE = "approval_workflows"
    STEP_TABLE = "approval_steps"
    HISTORY_TABLE = "approval_history"

    QUEUE_VIEW = "approval_queue"
    PENDING_VIEW = "pending_approvals"

    def workflows(self):
        return self.db.table(self.WORKFLOW_TABLE)

    def steps(self):
        return self.db.table(self.STEP_TABLE)

    def history(self):
        return self.db.table(self.HISTORY_TABLE)

    def queue(self):
        return self.db.table(self.QUEUE_VIEW)

    def pending(self):
        return self.db.table(self.PENDING_VIEW)
    
        # =========================================================
    # Workflow
    # =========================================================

    async def create_workflow(
        self,
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.workflows()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_workflow(
        self,
        workflow_id: str,
    ) -> dict | None:

        result = (
            self.workflows()
            .select("*")
            .eq("id", workflow_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def update_workflow(
        self,
        workflow_id: str,
        values: dict[str, Any],
    ) -> dict:

        values["updated_at"] = datetime.now(UTC)

        result = (
            self.workflows()
            .update(values)
            .eq("id", workflow_id)
            .execute()
        )

        return result.data[0]

    async def update_status(
        self,
        workflow_id: str,
        status: ApprovalStatus,
    ) -> dict:

        return await self.update_workflow(
            workflow_id,
            {
                "status": status.value,
            },
        )

    async def complete_workflow(
        self,
        workflow_id: str,
    ) -> dict:

        return await self.update_workflow(
            workflow_id,
            {
                "status": ApprovalStatus.APPROVED.value,
                "completed_at": datetime.now(UTC),
            },
        )
    
        # =========================================================
    # Approval Steps
    # =========================================================

    async def create_step(
        self,
        values: dict[str, Any],
    ) -> dict:
        """
        Create an approval step.
        """

        result = (
            self.steps()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_step(
        self,
        step_id: str,
    ) -> dict | None:
        """
        Get a workflow step by ID.
        """

        result = (
            self.steps()
            .select("*")
            .eq("id", step_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_workflow_steps(
        self,
        workflow_id: str,
    ) -> list[dict]:
        """
        List all steps for a workflow.
        """

        result = (
            self.steps()
            .select("*")
            .eq("workflow_id", workflow_id)
            .order("step_number")
            .execute()
        )

        return result.data or []

    async def list_pending_steps(
        self,
        org_id: str,
    ) -> list[dict]:
        """
        List all pending approval steps.
        Uses idx_steps_pending.
        """

        result = (
            self.steps()
            .select("*")
            .eq("org_id", org_id)
            .eq("decision", ApprovalDecision.PENDING.value)
            .order("step_number")
            .execute()
        )

        return result.data or []

    async def list_approver_tasks(
        self,
        approver_id: str,
    ) -> list[dict]:
        """
        List pending approval tasks assigned to an approver.
        Uses idx_steps_approver.
        """

        result = (
            self.steps()
            .select("*")
            .eq("approver_id", approver_id)
            .eq("decision", ApprovalDecision.PENDING.value)
            .order("due_date")
            .execute()
        )

        return result.data or []

    async def update_step_decision(
        self,
        step_id: str,
        decision: ApprovalDecision,
        comment: str | None = None,
    ) -> dict:
        """
        Record an approver's decision.
        """

        values = {
            "decision": decision.value,
            "decided_at": datetime.now(UTC),
        }

        if comment is not None:
            values["comment"] = comment

        result = (
            self.steps()
            .update(values)
            .eq("id", step_id)
            .execute()
        )

        return result.data[0]

    async def delegate_step(
        self,
        step_id: str,
        delegated_to: str,
        reason: str | None = None,
    ) -> dict:
        """
        Delegate an approval step.
        """

        values = {
            "delegated_to": delegated_to,
            "delegated_at": datetime.now(UTC),
        }

        if reason is not None:
            values["delegation_reason"] = reason

        result = (
            self.steps()
            .update(values)
            .eq("id", step_id)
            .execute()
        )

        return result.data[0]
    
        # =========================================================
    # Approval History
    # =========================================================

    async def record_action(
        self,
        values: dict[str, Any],
    ) -> dict:
        """
        Record an approval action.
        """

        result = (
            self.history()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_history(
        self,
        history_id: str,
    ) -> dict | None:
        """
        Get a history record.
        """

        result = (
            self.history()
            .select("*")
            .eq("id", history_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_workflow_history(
        self,
        workflow_id: str,
    ) -> list[dict]:
        """
        List workflow history.

        Uses idx_approval_hist_workflow.
        """

        result = (
            self.history()
            .select("*")
            .eq("workflow_id", workflow_id)
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return result.data or []

    async def list_organization_history(
        self,
        org_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        List organization approval history.

        Uses idx_approval_hist_org.
        """

        result = (
            self.history()
            .select("*")
            .eq("org_id", org_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []

    async def list_actor_history(
        self,
        actor_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        List actions performed by an approver.

        Uses idx_approval_hist_actor.
        """

        result = (
            self.history()
            .select("*")
            .eq("actor_id", actor_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []
    
        # =========================================================
    # Read Models (Views)
    # =========================================================

    async def list_queue(
        self,
        org_id: str,
    ) -> list[dict]:
        """
        List approval queue for an organization.
        Read-only PostgreSQL view.
        """

        result = (
            self.queue()
            .select("*")
            .eq("org_id", org_id)
            .execute()
        )

        return result.data or []

    async def list_pending_approvals(
        self,
        approver_id: str,
    ) -> list[dict]:
        """
        List pending approvals assigned to an approver.
        Read-only PostgreSQL view.
        """

        result = (
            self.pending()
            .select("*")
            .eq("approver_id", approver_id)
            .order(
                "due_date",
                desc=False,
            )
            .execute()
        )

        return result.data or []

    async def get_pending_document(
        self,
        document_id: str,
    ) -> dict | None:
        """
        Retrieve a pending approval by document.
        """

        result = (
            self.pending()
            .select("*")
            .eq("document_id", document_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    # =========================================================
    # Helpers
    # =========================================================

    async def workflow_exists(
        self,
        workflow_id: str,
    ) -> bool:
        """
        Check whether a workflow exists.
        """

        result = (
            self.workflows()
            .select("id")
            .eq("id", workflow_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def step_exists(
        self,
        step_id: str,
    ) -> bool:
        """
        Check whether an approval step exists.
        """

        result = (
            self.steps()
            .select("id")
            .eq("id", step_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def has_pending_steps(
        self,
        workflow_id: str,
    ) -> bool:
        """
        Determine whether a workflow still has pending steps.
        """

        result = (
            self.steps()
            .select("id")
            .eq("workflow_id", workflow_id)
            .eq("decision", ApprovalDecision.PENDING.value)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def count_pending_steps(
        self,
        workflow_id: str,
    ) -> int:
        """
        Count pending approval steps.
        """

        result = (
            self.steps()
            .select(
                "id",
                count="exact",
            )
            .eq("workflow_id", workflow_id)
            .eq("decision", ApprovalDecision.PENDING.value)
            .execute()
        )

        return result.count or 0