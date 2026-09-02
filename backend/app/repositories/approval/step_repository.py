"""
============================================================
Approval Step Repository

Persistence for approval_steps.

No business logic.
============================================================
"""


from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.enum.database import ApprovalDecision
from app.mappers.approval_mapper import ApprovalStepMapper
from app.models.domain.approval import ApprovalStep
from app.repositories.base import BaseRepository


class ApprovalStepRepository(BaseRepository):
    """
    Repository for approval_steps.
    """

    table_name = "approval_steps"
    mapper = ApprovalStepMapper

    # =========================================================
    # CRUD
    # =========================================================

    async def create_step(
        self,
        step: ApprovalStep | dict,
    ) -> ApprovalStep | None:

        return await self.create(step)

    async def get_step(
        self,
        step_id: UUID,
    ) -> ApprovalStep | None:

        return await self.get(step_id)

    async def update_step(
        self,
        step_id: UUID,
        data,
    ) -> ApprovalStep | None:

        if isinstance(data, dict):
            data["updated_at"] = datetime.now(UTC)

        return await self.update(
            step_id,
            data,
        )

    async def delete_step(
        self,
        step_id: UUID,
    ) -> bool:

        return await self.delete(step_id)

    # =========================================================
    # Queries
    # =========================================================

    async def list_workflow_steps(
        self,
        workflow_id: UUID,
    ) -> list[ApprovalStep]:

        response = (
            self.table()
            .select("*")
            .eq("workflow_id", str(workflow_id))
            .order("step_number")
            .execute()
        )

        return self._many(response)

    async def get_current_step(
        self,
        workflow_id: UUID,
    ) -> ApprovalStep | None:

        response = (
            self.table()
            .select("*")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .order("step_number")
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def list_pending_steps(
        self,
        org_id: UUID,
    ) -> list[ApprovalStep]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq(
                "decision",
                ApprovalDecision.PENDING.value,
            )
            .order("step_number")
            .execute()
        )

        return self._many(response)

    async def list_approver_tasks(
        self,
        approver_id: UUID,
    ) -> list[ApprovalStep]:

        response = (
            self.table()
            .select("*")
            .eq("approver_id", str(approver_id))
            .eq(
                "decision",
                ApprovalDecision.PENDING.value,
            )
            .order("due_date")
            .execute()
        )

        return self._many(response)

    async def list_overdue_steps(
        self,
        org_id: UUID,
    ) -> list[ApprovalStep]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .lt("due_date", datetime.now(UTC).isoformat())
            .order("due_date")
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Decisions
    # =========================================================

    async def update_decision(
        self,
        step_id: UUID,
        decision: ApprovalDecision,
        comment: str | None = None,
    ) -> ApprovalStep | None:

        values = {
            "decision": decision.value,
            "decided_at": datetime.now(UTC),
        }

        if comment is not None:
            values["comment"] = comment

        return await self.update_step(
            step_id,
            values,
        )

    async def approve(
        self,
        step_id: UUID,
        comment: str | None = None,
    ) -> ApprovalStep | None:

        return await self.update_decision(
            step_id,
            ApprovalDecision.APPROVED,
            comment,
        )

    async def reject(
        self,
        step_id: UUID,
        comment: str | None = None,
    ) -> ApprovalStep | None:

        return await self.update_decision(
            step_id,
            ApprovalDecision.REJECTED,
            comment,
        )

    async def delegate(
    self,
    step_id: UUID,
    delegated_to: UUID,
    reason: str | None = None,
) -> ApprovalStep | None:

        values = {
            "decision": ApprovalDecision.DELEGATED.value,
            "delegated_to": str(delegated_to),
            "delegated_at": datetime.now(UTC),
        }

        if reason is not None:
            values["delegation_reason"] = reason

        return await self.update_step(
            step_id,
            values,
        )

    async def send_reminder(
        self,
        step_id: UUID,
    ) -> ApprovalStep | None:

        return await self.update_step(
            step_id,
            {
                "reminder_sent_at": datetime.now(UTC),
            },
        )

    async def mark_escalated(
        self,
        step_id: UUID,
    ) -> ApprovalStep | None:

        return await self.update_step(
            step_id,
            {
                "escalated_at": datetime.now(UTC),
            },
        )

    # =========================================================
    # Helpers
    # =========================================================

    async def step_exists(
        self,
        step_id: UUID,
    ) -> bool:

        return await self.exists(
            "id",
            step_id,
        )

    async def pending_count(
        self,
        workflow_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select("id", count="exact")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .execute()
        )

        return response.count or 0
    async def list_due_for_reminder(
        self,
        org_id: UUID,
        *,
        reminder_window_minutes: int = 60,
    ) -> list[ApprovalStep]:
        cutoff = datetime.now(UTC) + timedelta(minutes=reminder_window_minutes)
        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .is_("reminder_sent_at", "null")
            .not_.is_("due_date", "null")
            .lte("due_date", cutoff.isoformat())
            .order("due_date")
            .execute()
        )
        return self._many(response)
