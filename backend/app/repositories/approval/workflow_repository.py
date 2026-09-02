"""
============================================================
Approval Workflow Repository

Persistence for approval_workflows.

No business logic.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.application import ApprovalStatus
from app.core.enum.database import ApprovalDecision
from app.mappers.approval_mapper import ApprovalWorkflowMapper
from app.models.domain.approval import ApprovalWorkflow
from app.repositories.base import BaseRepository


class ApprovalWorkflowRepository(BaseRepository):
    """
    Repository for approval workflows.
    """

    table_name = "approval_workflows"
    mapper = ApprovalWorkflowMapper

    PENDING_VIEW = "pending_approvals"
    QUEUE_VIEW = "approval_queue"

    # =========================================================
    # Views
    # =========================================================

    def pending(self):
        return self.db.table(self.PENDING_VIEW)

    def queue(self):
        return self.db.table(self.QUEUE_VIEW)

    # =========================================================
    # CRUD
    # =========================================================

    async def create_workflow(
        self,
        workflow: ApprovalWorkflow | dict,
    ) -> ApprovalWorkflow | None:
        return await self.create(workflow)

    async def get_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow | None:
        return await self.get(workflow_id)

    async def update_workflow(
        self,
        workflow_id: UUID,
        data,
    ) -> ApprovalWorkflow | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            workflow_id,
            data,
        )

    async def delete_workflow(
        self,
        workflow_id: UUID,
    ) -> bool:
        return await self.delete(workflow_id)

    # =========================================================
    # Workflow Actions
    # =========================================================

    async def update_status(
        self,
        workflow_id: UUID,
        status: ApprovalStatus,
    ) -> ApprovalWorkflow | None:

        return await self.update_workflow(
            workflow_id,
            {
                "status": status.value,
            },
        )

    async def complete_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow | None:

        return await self.update_workflow(
            workflow_id,
            {
                "status": ApprovalStatus.APPROVED.value,
                "completed_at": datetime.now(UTC),
            },
        )

    async def reject_workflow(
        self,
        workflow_id: UUID,
    ) -> ApprovalWorkflow | None:

        return await self.update_workflow(
            workflow_id,
            {
                "status": ApprovalStatus.REJECTED.value,
                "completed_at": datetime.now(UTC),
            },
        )

    # =========================================================
    # Queries
    # =========================================================

    async def get_document_workflow(
        self,
        document_id: UUID,
    ) -> ApprovalWorkflow | None:

        response = (
            self.table()
            .select("*")
            .eq("document_id", str(document_id))
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_organization_workflows(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ApprovalWorkflow]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return self._many(response)

    async def list_by_status(
        self,
        org_id: UUID,
        status: ApprovalStatus,
    ) -> list[ApprovalWorkflow]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("status", status.value)
            .order("created_at", desc=True)
            .execute()
        )

        return self._many(response)

    async def pending_queue(
        self,
        org_id: UUID,
    ):

        response = (
            self.pending()
            .select("*")
            .eq("org_id", str(org_id))
            .execute()
        )

        return response.data or []

    async def approval_queue(
        self,
        org_id: UUID,
    ):

        response = (
            self.queue()
            .select("*")
            .eq("org_id", str(org_id))
            .execute()
        )

        return response.data or []

    # =========================================================
    # Helpers
    # =========================================================

    async def workflow_exists(
        self,
        workflow_id: UUID,
    ) -> bool:
        return await self.exists(
            "id",
            workflow_id,
        )

    async def has_pending_steps(
        self,
        workflow_id: UUID,
    ) -> bool:

        response = (
            self.db.table("approval_steps")
            .select("id")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .limit(1)
            .execute()
        )

        return bool(response.data)

    async def pending_step_count(
        self,
        workflow_id: UUID,
    ) -> int:

        response = (
            self.db.table("approval_steps")
            .select("id", count="exact")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .execute()
        )

        return response.count or 0