
"""
============================================================
Approval History Service
============================================================

Application service for approval audit history.

Responsibilities:
- Create immutable approval history events
- Retrieve individual history events
- Retrieve workflow history
- Retrieve step history
- Retrieve actor history
- Retrieve organization/admin audit history
- Apply business-level filtering
- Handle cursor pagination
- Convert domain models to API responses

The repository owns database persistence.
The service owns application orchestration.

Approval history is append-only.
Existing history records are never updated or deleted.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.domain.approval import ApprovalHistory
from app.repositories.approval.history_repository import (
    ApprovalHistoryRepository,
)
from app.schemas.approval import (
    ApprovalHistoryResponse,
)


class ApprovalHistoryService:
    """
    Application service for approval history.
    """

    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200

    def __init__(
        self,
        repository: ApprovalHistoryRepository,
    ) -> None:
        self.repository = repository

    # =========================================================
    # CREATE
    # =========================================================

    async def create_history(
        self,
        history: ApprovalHistory,
    ) -> ApprovalHistoryResponse:
        """
        Create an immutable approval history event.
        """

        created = await self.repository.create_history(
            history
        )

        if created is None:
            raise RuntimeError(
                "Failed to create approval history event."
            )

        return ApprovalHistoryResponse.model_validate(
            created
        )

    # =========================================================
    # GET
    # =========================================================

    async def get_history(
        self,
        history_id: UUID,
    ) -> ApprovalHistoryResponse | None:
        """
        Retrieve one approval history event.
        """

        history = await self.repository.get_history(
            history_id
        )

        if history is None:
            return None

        return ApprovalHistoryResponse.model_validate(
            history
        )

    # =========================================================
    # WORKFLOW HISTORY
    # =========================================================

    async def get_workflow_history(
        self,
        workflow_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve workflow audit history using cursor pagination.
        """

        limit = self._normalize_limit(limit)

        before_created_at, before_id = self._decode_cursor(
            cursor
        )

        history = (
            await self.repository.list_workflow_history_page(
                workflow_id=workflow_id,
                limit=limit + 1,
                before_created_at=before_created_at,
                before_id=before_id,
            )
        )

        has_more = len(history) > limit

        if has_more:
            history = history[:limit]

        items = self._serialize_many(history)

        next_cursor = None

        if has_more and history:
            next_cursor = self._encode_cursor(
                history[-1]
            )

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    # =========================================================
    # STEP HISTORY
    # =========================================================

    async def get_step_history(
        self,
        step_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve approval-step audit history.
        """

        limit = self._normalize_limit(limit)

        before_created_at, before_id = self._decode_cursor(
            cursor
        )

        history = (
            await self.repository.list_step_history_page(
                step_id=step_id,
                limit=limit + 1,
                before_created_at=before_created_at,
                before_id=before_id,
            )
        )

        has_more = len(history) > limit

        if has_more:
            history = history[:limit]

        items = self._serialize_many(history)

        next_cursor = None

        if has_more and history:
            next_cursor = self._encode_cursor(
                history[-1]
            )

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    # =========================================================
    # ACTOR HISTORY
    # =========================================================

    async def get_actor_history(
        self,
        actor_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve audit events generated by an actor.
        """

        limit = self._normalize_limit(limit)

        before_created_at, before_id = self._decode_cursor(
            cursor
        )

        history = (
            await self.repository.list_actor_history_page(
                actor_id=actor_id,
                limit=limit + 1,
                before_created_at=before_created_at,
                before_id=before_id,
            )
        )

        has_more = len(history) > limit

        if has_more:
            history = history[:limit]

        items = self._serialize_many(history)

        next_cursor = None

        if has_more and history:
            next_cursor = self._encode_cursor(
                history[-1]
            )

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    # =========================================================
    # ORGANIZATION HISTORY
    # =========================================================

    async def get_organization_history(
        self,
        org_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve organization-wide audit history.

        This is the primary service method for:
        - Admin audit logs
        - Organization audit timelines
        - Compliance history
        """

        limit = self._normalize_limit(limit)

        before_created_at, before_id = self._decode_cursor(
            cursor
        )

        history = (
            await self.repository
            .list_organization_history_page(
                org_id=org_id,
                limit=limit + 1,
                before_created_at=before_created_at,
                before_id=before_id,
            )
        )

        has_more = len(history) > limit

        if has_more:
            history = history[:limit]

        items = self._serialize_many(history)

        next_cursor = None

        if has_more and history:
            next_cursor = self._encode_cursor(
                history[-1]
            )

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    # =========================================================
    # ADMIN AUDIT SEARCH
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
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Search organization approval history.

        Every query remains scoped to org_id.
        """

        limit = self._normalize_limit(limit)

        self._validate_date_range(
            start_at,
            end_at,
        )

        before_created_at, before_id = self._decode_cursor(
            cursor
        )

        history = (
            await self.repository
            .search_organization_history(
                org_id=org_id,
                action=action,
                new_status=new_status,
                old_status=old_status,
                actor_id=actor_id,
                workflow_id=workflow_id,
                step_id=step_id,
                start_at=start_at,
                end_at=end_at,
                limit=limit + 1,
                before_created_at=before_created_at,
                before_id=before_id,
            )
        )

        has_more = len(history) > limit

        if has_more:
            history = history[:limit]

        items = self._serialize_many(history)

        next_cursor = None

        if has_more and history:
            next_cursor = self._encode_cursor(
                history[-1]
            )

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    # =========================================================
    # LATEST EVENT
    # =========================================================

    async def get_latest_workflow_action(
        self,
        workflow_id: UUID,
    ) -> ApprovalHistoryResponse | None:
        """
        Return the most recent audit event for a workflow.
        """

        history = await self.repository.latest_action(
            workflow_id
        )

        if history is None:
            return None

        return ApprovalHistoryResponse.model_validate(
            history
        )

    # =========================================================
    # EXISTENCE
    # =========================================================

    async def history_exists(
        self,
        history_id: UUID,
    ) -> bool:
        """
        Check whether an audit event exists.
        """

        return await self.repository.history_exists(
            history_id
        )

    async def workflow_has_history(
        self,
        workflow_id: UUID,
    ) -> bool:
        """
        Check whether a workflow has audit history.
        """

        return await self.repository.workflow_has_history(
            workflow_id
        )

    # =========================================================
    # COUNTS
    # =========================================================

    async def count_workflow_events(
        self,
        workflow_id: UUID,
    ) -> int:
        """
        Count workflow audit events.
        """

        return await self.repository.count_workflow_events(
            workflow_id
        )

    async def count_organization_events(
        self,
        org_id: UUID,
    ) -> int:
        """
        Count organization audit events.
        """

        return await self.repository.count_organization_events(
            org_id
        )

    # =========================================================
    # SERIALIZATION
    # =========================================================

    @staticmethod
    def _serialize(
        history: ApprovalHistory,
    ) -> ApprovalHistoryResponse:
        """
        Convert domain model to API response.
        """

        return ApprovalHistoryResponse.model_validate(
            history
        )

    @classmethod
    def _serialize_many(
        cls,
        history: list[ApprovalHistory],
    ) -> list[ApprovalHistoryResponse]:
        """
        Convert multiple domain objects to API responses.
        """

        return [
            cls._serialize(item)
            for item in history
        ]

    # =========================================================
    # CURSOR
    # =========================================================

    @staticmethod
    def _encode_cursor(
        history: ApprovalHistory,
    ) -> str:
        """
        Encode the last record's ordering fields
        into an opaque cursor.

        Cursor payload:

            {
                "created_at": "...",
                "id": "..."
            }
        """

        payload = {
            "created_at": history.created_at.isoformat(),
            "id": str(history.id),
        }

        raw = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")

        return base64.urlsafe_b64encode(
            raw
        ).decode("ascii")

    @staticmethod
    def _decode_cursor(
        cursor: str | None,
    ) -> tuple[datetime | None, UUID | None]:
        """
        Decode and validate an opaque pagination cursor.
        """

        if not cursor:
            return None, None

        try:
            raw = base64.urlsafe_b64decode(
                cursor.encode("ascii")
            )

            payload = json.loads(
                raw.decode("utf-8")
            )

            created_at = datetime.fromisoformat(
                payload["created_at"]
            )

            history_id = UUID(
                payload["id"]
            )

        except (
            ValueError,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError(
                "Invalid approval history cursor."
            ) from exc

        return created_at, history_id

    # =========================================================
    # VALIDATION
    # =========================================================

    @classmethod
    def _normalize_limit(
        cls,
        limit: int,
    ) -> int:
        """
        Normalize pagination size.
        """

        if limit <= 0:
            return cls.DEFAULT_PAGE_SIZE

        return min(
            limit,
            cls.MAX_PAGE_SIZE,
        )

    @staticmethod
    def _validate_date_range(
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> None:
        """
        Validate audit search date range.
        """

        if (
            start_at is not None
            and end_at is not None
            and start_at >= end_at
        ):
            raise ValueError(
                "start_at must be earlier than end_at."
            )

