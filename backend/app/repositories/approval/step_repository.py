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
from app.core.db import execute


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

    async def create_steps(
        self,
        steps: list[ApprovalStep | dict],
    ) -> list[ApprovalStep]:
        """Insert every step of a workflow in one statement.

        A workflow with N approval stages used to cost N inserts. The domain
        objects already carry their ids, so the caller does not need the
        inserted representation back.
        """

        if not steps:
            return []

        payload = [self.mapper.to_insert(step) for step in steps]

        response = await execute(self.table().insert(payload))

        created = self.mapper.to_domain_list(response.data or [])

        # PostgREST returns the inserted rows unless representation is
        # suppressed; fall back to the caller's objects when it does not.
        return created if len(created) == len(payload) else list(steps)

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

    async def update_steps(
        self,
        step_ids: list[UUID],
        data,
        *,
        org_id: UUID | None = None,
    ) -> list[ApprovalStep]:
        """Apply the same change to several steps in one statement.

        Used when a decision resolves a whole stage (withdrawing the other
        approvers, or activating every step of the next stage). The previous
        per-step ``update_step`` calls cost one round trip per approver.

        ``org_id`` is an optional tenant guard: when it is supplied the update
        also filters on it, so a step id from another organization can never be
        touched even if it were passed in by mistake.
        """

        if not step_ids:
            return []

        payload = self.mapper.to_update(data)
        payload["updated_at"] = datetime.now(UTC)

        query = self.table().update(payload).in_(
            "id", [str(step_id) for step_id in step_ids]
        )
        if org_id is not None:
            query = query.eq("org_id", str(org_id))
        response = await execute(query)

        return self._many(response)

    async def claim_group_step(self, step_id: UUID, user_id: UUID) -> ApprovalStep | None:
        """Atomically claim an unclaimed pending group step."""
        response = await execute(
            self.table()
            .update({
                "approver_id": str(user_id),
                "claimed_by": str(user_id),
                "claimed_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            })
            .eq("id", str(step_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .is_("claimed_by", "null")
        )
        return self._one(response)

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

        response = await execute(
            self.table()
            .select("*")
            .eq("workflow_id", str(workflow_id))
            .order("step_number")
        )

        return self._many(response)

    async def list_steps_for_workflows(
        self,
        workflow_ids: list[UUID],
    ) -> dict[str, list[ApprovalStep]]:
        """Return each workflow's steps in one query, grouped by workflow id."""

        if not workflow_ids:
            return {}

        response = await execute(
            self.table()
            .select("*")
            .in_("workflow_id", [str(workflow_id) for workflow_id in workflow_ids])
            .order("step_number")
        )

        grouped: dict[str, list[ApprovalStep]] = {}
        for step in self._many(response):
            grouped.setdefault(str(step.workflow_id), []).append(step)
        return grouped

    async def get_current_step(
        self,
        workflow_id: UUID,
    ) -> ApprovalStep | None:

        response = await execute(
            self.table()
            .select("*")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .order("step_number")
            .limit(1)
        )

        return self._one(response)

    async def list_pending_steps(
        self,
        org_id: UUID,
    ) -> list[ApprovalStep]:

        response = await execute(
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq(
                "decision",
                ApprovalDecision.PENDING.value,
            )
            .order("step_number")
        )

        return self._many(response)

    async def list_approver_tasks(
        self,
        approver_id: UUID,
    ) -> list[ApprovalStep]:

        response = await execute(
            self.table()
            .select("*")
            .eq("approver_id", str(approver_id))
            .eq(
                "decision",
                ApprovalDecision.PENDING.value,
            )
            .order("due_date")
        )

        return self._many(response)

    async def list_overdue_steps(
        self,
        org_id: UUID,
    ) -> list[ApprovalStep]:

        response = await execute(
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .lt("due_date", datetime.now(UTC).isoformat())
            .order("due_date")
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

        response = await execute(
            self.table()
            .select("id", count="exact")
            .eq("workflow_id", str(workflow_id))
            .eq("decision", ApprovalDecision.PENDING.value)
        )

        return response.count or 0
    async def list_due_for_reminder(
        self,
        org_id: UUID,
        *,
        reminder_window_minutes: int = 60,
    ) -> list[ApprovalStep]:
        cutoff = datetime.now(UTC) + timedelta(minutes=reminder_window_minutes)
        response = await execute(
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("decision", ApprovalDecision.PENDING.value)
            .is_("reminder_sent_at", "null")
            .not_.is_("due_date", "null")
            .lte("due_date", cutoff.isoformat())
            .order("due_date")
        )
        return self._many(response)
