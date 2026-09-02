"""
============================================================
Approval History Repository
============================================================

Persistence layer for approval_history.

Design goals:
- Append-only audit trail
- Organization/tenant scoped queries
- Keyset/cursor pagination
- Stable ordering
- Efficient indexed queries
- Workflow/step/actor filtering
- Action/status filtering
- Date-range filtering
- Latest-event queries
- Event counting
- No business logic

IMPORTANT:
Approval history is an audit log.

There is intentionally NO update_history() method.
Existing audit records should not be mutated.
A correction should create a new history event.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.mappers.approval_mapper import ApprovalHistoryMapper
from app.models.domain.approval import ApprovalHistory
from app.repositories.base import BaseRepository


class ApprovalHistoryRepository(BaseRepository):
    """
    Repository for the approval_history table.

    History records are append-only.
    """

    table_name = "approval_history"
    mapper = ApprovalHistoryMapper

    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200

    # =========================================================
    # CREATE
    # =========================================================

    async def create_history(
        self,
        history: ApprovalHistory | dict[str, Any],
    ) -> ApprovalHistory | None:
        """
        Create an immutable audit event.

        No update operation is exposed intentionally.
        """

        return await self.create(history)

    # =========================================================
    # READ
    # =========================================================

    async def get_history(
        self,
        history_id: UUID,
    ) -> ApprovalHistory | None:
        """
        Retrieve one history event by primary key.
        """

        return await self.get(history_id)

    async def history_exists(
        self,
        history_id: UUID,
    ) -> bool:
        """
        Check whether an audit event exists.
        """

        return await self.exists(
            "id",
            history_id,
        )

    # =========================================================
    # WORKFLOW HISTORY
    # =========================================================

    async def list_workflow_history(
        self,
        workflow_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return workflow history newest first.

        This is intended for small/simple timeline reads.
        Use list_workflow_history_page() for large datasets.
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("workflow_id", str(workflow_id))
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def workflow_has_history(
        self,
        workflow_id: UUID,
    ) -> bool:
        """
        Fast existence check for workflow history.
        """

        response = (
            self.table()
            .select("id")
            .eq("workflow_id", str(workflow_id))
            .limit(1)
            .execute()
        )

        return bool(response.data)

    async def latest_action(
        self,
        workflow_id: UUID,
    ) -> ApprovalHistory | None:
        """
        Return the latest audit event for a workflow.
        """

        response = (
            self.table()
            .select("*")
            .eq("workflow_id", str(workflow_id))
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )

        return self._one(response)

    # =========================================================
    # WORKFLOW HISTORY - KEYSET PAGINATION
    # =========================================================

    async def list_workflow_history_page(
        self,
        workflow_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
    ) -> list[ApprovalHistory]:
        """
        Keyset-paginated workflow history.

        Ordering:
            created_at DESC
            id DESC

        The cursor consists of:
            before_created_at
            before_id

        This is substantially more scalable than OFFSET pagination
        for large audit tables.
        """

        limit = self._normalize_limit(limit)

        query = (
            self.table()
            .select("*")
            .eq("workflow_id", str(workflow_id))
        )

        if before_created_at is not None:
            if before_id is not None:
                cursor_timestamp = before_created_at.isoformat()

                query = query.or_(
                    f"created_at.lt.{cursor_timestamp},"
                    f"and(created_at.eq.{cursor_timestamp},"
                    f"id.lt.{before_id})"
                )
            else:
                query = query.lt(
                    "created_at",
                    before_created_at.isoformat(),
                )

        response = (
            query
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # STEP HISTORY
    # =========================================================

    async def list_step_history(
        self,
        step_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return history for one approval step.
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("step_id", str(step_id))
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_step_history_page(
        self,
        step_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
    ) -> list[ApprovalHistory]:
        """
        Keyset-paginated history for one approval step.
        """

        limit = self._normalize_limit(limit)

        query = (
            self.table()
            .select("*")
            .eq("step_id", str(step_id))
        )

        query = self._apply_cursor(
            query,
            before_created_at,
            before_id,
        )

        response = (
            query
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # ACTOR HISTORY
    # =========================================================

    async def list_actor_history(
        self,
        actor_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return audit events generated by one actor.
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("actor_id", str(actor_id))
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_actor_history_page(
        self,
        actor_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
    ) -> list[ApprovalHistory]:
        """
        Keyset-paginated actor audit history.
        """

        limit = self._normalize_limit(limit)

        query = (
            self.table()
            .select("*")
            .eq("actor_id", str(actor_id))
        )

        query = self._apply_cursor(
            query,
            before_created_at,
            before_id,
        )

        response = (
            query
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # ORGANIZATION HISTORY
    # =========================================================

    async def list_organization_history(
        self,
        org_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return organization-wide approval history.

        Always scope this query by org_id.
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_organization_history_page(
        self,
        org_id: UUID,
        limit: int = DEFAULT_PAGE_SIZE,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
    ) -> list[ApprovalHistory]:
        """
        Keyset-paginated organization audit history.

        This should be the primary method for an admin audit log.
        """

        limit = self._normalize_limit(limit)

        query = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
        )

        query = self._apply_cursor(
            query,
            before_created_at,
            before_id,
        )

        response = (
            query
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # ACTION FILTERING
    # =========================================================

    async def list_by_action(
        self,
        org_id: UUID,
        action: str,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return organization events matching an action.

        Example actions:
            created
            submitted
            approved
            rejected
            delegated
            escalated
            cancelled
            completed
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("action", action)
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_by_action_page(
        self,
        org_id: UUID,
        action: str,
        limit: int = DEFAULT_PAGE_SIZE,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
    ) -> list[ApprovalHistory]:
        """
        Keyset-paginated action search.
        """

        limit = self._normalize_limit(limit)

        query = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("action", action)
        )

        query = self._apply_cursor(
            query,
            before_created_at,
            before_id,
        )

        response = (
            query
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # STATUS FILTERING
    # =========================================================

    async def list_by_new_status(
        self,
        org_id: UUID,
        status: str,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return events that transitioned workflows into a status.
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("new_status", status)
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def list_by_old_status(
        self,
        org_id: UUID,
        status: str,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return events that transitioned workflows away from a status.
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("old_status", status)
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # DATE RANGE
    # =========================================================

    async def list_organization_history_between(
        self,
        org_id: UUID,
        start_at: datetime,
        end_at: datetime,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[ApprovalHistory]:
        """
        Return organization audit events within a time range.
        """

        limit = self._normalize_limit(limit)

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .gte("created_at", start_at.isoformat())
            .lt("created_at", end_at.isoformat())
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # COMBINED AUDIT QUERY
    # =========================================================

    async def search_organization_history(
        self,
        org_id: UUID,
        *,
        action: str | None = None,
        new_status: str | None = None,
        old_status: str | None = None,
        actor_id: UUID | None = None,
        workflow_id: UUID | None = None,
        step_id: UUID | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
    ) -> list[ApprovalHistory]:
        """
        Flexible organization audit search.

        Every query remains organization-scoped.

        Optional filters are only added when supplied.
        """

        limit = self._normalize_limit(limit)

        query = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
        )

        if action is not None:
            query = query.eq(
                "action",
                action,
            )

        if new_status is not None:
            query = query.eq(
                "new_status",
                new_status,
            )

        if old_status is not None:
            query = query.eq(
                "old_status",
                old_status,
            )

        if actor_id is not None:
            query = query.eq(
                "actor_id",
                str(actor_id),
            )

        if workflow_id is not None:
            query = query.eq(
                "workflow_id",
                str(workflow_id),
            )

        if step_id is not None:
            query = query.eq(
                "step_id",
                str(step_id),
            )

        if start_at is not None:
            query = query.gte(
                "created_at",
                start_at.isoformat(),
            )

        if end_at is not None:
            query = query.lt(
                "created_at",
                end_at.isoformat(),
            )

        query = self._apply_cursor(
            query,
            before_created_at,
            before_id,
        )

        response = (
            query
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # COUNTS
    # =========================================================

    async def count_workflow_events(
        self,
        workflow_id: UUID,
    ) -> int:
        """
        Count all events belonging to a workflow.
        """

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq(
                "workflow_id",
                str(workflow_id),
            )
            .execute()
        )

        return response.count or 0

    async def count_organization_events(
        self,
        org_id: UUID,
    ) -> int:
        """
        Count organization audit events.
        """

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq(
                "org_id",
                str(org_id),
            )
            .execute()
        )

        return response.count or 0

    # =========================================================
    # PRIVATE HELPERS
    # =========================================================

    @classmethod
    def _normalize_limit(
        cls,
        limit: int,
    ) -> int:
        """
        Prevent unbounded/abusive result sizes.
        """

        if limit <= 0:
            return cls.DEFAULT_PAGE_SIZE

        return min(
            limit,
            cls.MAX_PAGE_SIZE,
        )

    @staticmethod
    def _apply_cursor(
        query,
        before_created_at: datetime | None,
        before_id: UUID | None,
    ):
        """
        Apply keyset pagination cursor.

        Sort order:
            created_at DESC
            id DESC

        For a previous page cursor:

            created_at < cursor_created_at

        OR:

            created_at = cursor_created_at
            id < cursor_id
        """

        if before_created_at is None:
            return query

        timestamp = before_created_at.isoformat()

        if before_id is None:
            return query.lt(
                "created_at",
                timestamp,
            )

        return query.or_(
            f"created_at.lt.{timestamp},"
            f"and(created_at.eq.{timestamp},"
            f"id.lt.{before_id})"
        )
