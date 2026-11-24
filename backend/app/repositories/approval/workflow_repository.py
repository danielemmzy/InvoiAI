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
from app.core.db import execute


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

        response = await execute(
            self.table()
            .select("*")
            .eq("document_id", str(document_id))
            .limit(1)
        )

        return self._one(response)

    async def list_organization_workflows(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ApprovalWorkflow]:

        response = await execute(
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        return self._many(response)

    async def list_by_status(
        self,
        org_id: UUID,
        status: ApprovalStatus,
    ) -> list[ApprovalWorkflow]:

        response = await execute(
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("status", status.value)
            .order("created_at", desc=True)
        )

        return self._many(response)

    async def pending_queue(
        self,
        org_id: UUID,
    ):

        response = await execute(
            self.pending()
            .select("*")
            .eq("org_id", str(org_id))
        )

        return response.data or []

    async def approval_queue(
        self,
        org_id: UUID,
    ):

        response = await execute(
            self.queue()
            .select("*")
            .eq("org_id", str(org_id))
        )

        return response.data or []

    async def approval_queue_for_user(self, org_id: UUID, user_id: UUID) -> list[dict]:
        """Return pending individual and pooled/group tasks visible to one user.

        The legacy approval_queue view only keys tasks by approver_id, so
        unclaimed group steps (where approver_id is NULL) cannot appear in
        the normal user queue. This read model joins the canonical step,
        workflow, document and analysis tables and expands group membership
        explicitly.
        """
        group_rows = (
            await execute(
                self.db.table("ap_approval_group_members")
                .select("group_id")
                .eq("user_id", str(user_id))
            )
        ).data or []
        group_ids = [str(r["group_id"]) for r in group_rows if r.get("group_id")]

        query = (
            self.db.table("approval_steps")
            .select(
                "id,workflow_id,step_number,step_name,approver_id,approver_group_id,"
                "claimed_by,decision,due_date,auto_escalated"
            )
            .eq("org_id", str(org_id))
            .eq("decision", ApprovalDecision.PENDING.value)
        )
        rows = (await execute(query)).data or []

        visible = []
        for row in rows:
            approver = str(row.get("approver_id") or "")
            group = str(row.get("approver_group_id") or "")
            claimed = str(row.get("claimed_by") or "")
            if approver == str(user_id) or claimed == str(user_id):
                visible.append(row)
            elif group and group in group_ids and not row.get("claimed_by"):
                visible.append(row)

        if not visible:
            return []

        workflow_ids = list({str(r["workflow_id"]) for r in visible})
        workflows = (
            await execute(
                self.db.table("approval_workflows").select(
                    "id,document_id,initiated_at,due_date,is_urgent,status"
                ).eq("org_id", str(org_id)).in_("id", workflow_ids)
            )
        ).data or []
        workflow_map = {str(r["id"]): r for r in workflows}

        document_ids = list({str(workflow_map[str(r["workflow_id"])]["document_id"]) for r in visible if str(r["workflow_id"]) in workflow_map})
        documents = (
            await execute(
                self.db.table("documents").select(
                    "id,document_number,vendor_name,total_amount,currency,document_type"
                ).eq("org_id", str(org_id)).in_("id", document_ids)
            )
        ).data or []
        document_map = {str(r["id"]): r for r in documents}

        analyses = (
            await execute(
                self.db.table("document_analyses").select(
                    "document_id,health_score,risk_level,recommendation,created_at"
                ).eq("org_id", str(org_id)).in_("document_id", document_ids)
                .order("created_at", desc=True)
            )
        ).data or []
        analysis_map = {}
        for row in analyses:
            analysis_map.setdefault(str(row["document_id"]), row)

        result = []
        for step in visible:
            workflow = workflow_map.get(str(step["workflow_id"]))
            if not workflow:
                continue
            document = document_map.get(str(workflow["document_id"]), {})
            analysis = analysis_map.get(str(workflow["document_id"]), {})
            result.append({
                "approver_id": step.get("approver_id"),
                "approver_group_id": step.get("approver_group_id"),
                "claimed_by": step.get("claimed_by"),
                "org_id": str(org_id),
                "workflow_id": step["workflow_id"],
                "step_id": step["id"],
                "step_name": step["step_name"],
                "step_number": step["step_number"],
                "due_date": step.get("due_date") or workflow.get("due_date"),
                "document_id": workflow["document_id"],
                "document_number": document.get("document_number"),
                "vendor_name": document.get("vendor_name"),
                "total_amount": document.get("total_amount") or 0,
                "currency": document.get("currency") or "USD",
                "document_type": document.get("document_type") or "invoice",
                "health_score": analysis.get("health_score"),
                "risk_level": analysis.get("risk_level"),
                "recommendation": analysis.get("recommendation"),
                "is_urgent": bool(workflow.get("is_urgent")),
                "initiated_at": workflow.get("initiated_at"),
            })
        return result

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

        response = await execute(
            self.db.table("approval_steps")
            .select("id")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .limit(1)
        )

        return bool(response.data)

    async def pending_step_count(
        self,
        workflow_id: UUID,
    ) -> int:

        response = await execute(
            self.db.table("approval_steps")
            .select("id", count="exact")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
        )

        return response.count or 0
