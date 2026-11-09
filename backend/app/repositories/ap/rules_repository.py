"""
AP Approval Rules Repository

Persistence layer for configurable AP approval/routing rules.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase


class ApprovalRuleRepository:
    TABLE = "ap_approval_rules"

    def __init__(self) -> None:
        self.supabase = get_supabase()

    async def list(
        self,
        org_id: UUID,
        *,
        scope: str | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        query = (
            self.supabase
            .table(self.TABLE)
            .select("*")
            .eq("org_id", str(org_id))
        )

        if scope:
            query = query.eq("scope", scope)

        if active_only:
            query = query.eq("is_active", True)

        response = (
            query
            .order("priority", desc=False)
            .order("created_at", desc=False)
            .execute()
        )

        return response.data or []

    async def get(
        self,
        org_id: UUID,
        rule_id: UUID,
    ) -> dict[str, Any] | None:
        response = (
            self.supabase
            .table(self.TABLE)
            .select("*")
            .eq("org_id", str(org_id))
            .eq("id", str(rule_id))
            .limit(1)
            .execute()
        )

        rows = response.data or []

        return rows[0] if rows else None

    async def create(
        self,
        org_id: UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        payload = dict(data)
        payload["org_id"] = str(org_id)

        response = (
            self.supabase
            .table(self.TABLE)
            .insert(payload)
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError(
                "Failed to create AP approval rule."
            )

        return rows[0]

    async def update(
        self,
        org_id: UUID,
        rule_id: UUID,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        payload = {
            key: value
            for key, value in data.items()
            if value is not None
        }

        response = (
            self.supabase
            .table(self.TABLE)
            .update(payload)
            .eq("org_id", str(org_id))
            .eq("id", str(rule_id))
            .execute()
        )

        rows = response.data or []

        return rows[0] if rows else None

    async def delete(
        self,
        org_id: UUID,
        rule_id: UUID,
    ) -> bool:
        response = (
            self.supabase
            .table(self.TABLE)
            .delete()
            .eq("org_id", str(org_id))
            .eq("id", str(rule_id))
            .execute()
        )

        return bool(response.data)

    async def set_active(
        self,
        org_id: UUID,
        rule_id: UUID,
        is_active: bool,
    ) -> dict[str, Any] | None:
        response = (
            self.supabase
            .table(self.TABLE)
            .update({"is_active": is_active})
            .eq("org_id", str(org_id))
            .eq("id", str(rule_id))
            .execute()
        )

        rows = response.data or []

        return rows[0] if rows else None