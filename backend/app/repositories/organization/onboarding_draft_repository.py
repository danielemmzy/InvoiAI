from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.db import execute
from app.core.supabase import get_supabase


class OnboardingDraftRepository:
    """Persistence for the single resumable draft owned by each user."""

    def __init__(self) -> None:
        self.db = get_supabase()

    async def get(self, user_id: UUID) -> dict[str, Any] | None:
        response = await execute(
            self.db.table("onboarding_drafts").select("*").eq("user_id", str(user_id)).limit(1)
        )
        rows = response.data or []
        return rows[0] if rows else None

    async def save(self, user_id: UUID, *, step: int, data: dict[str, Any]) -> dict[str, Any]:
        existing = await self.get(user_id)
        table = self.db.table("onboarding_drafts")
        if existing:
            response = await execute(
                table.update({"step": step, "data": data, "updated_at": datetime.now(UTC).isoformat()}).eq("user_id", str(user_id))
            )
        else:
            try:
                response = await execute(
                    table.insert({"user_id": str(user_id), "step": step, "data": data})
                )
            except Exception:
                # Concurrent first saves can race the one-draft-per-user unique key.
                if await self.get(user_id) is None:
                    raise
                response = await execute(
                    table.update({"step": step, "data": data, "updated_at": datetime.now(UTC).isoformat()}).eq("user_id", str(user_id))
                )
        rows = response.data or []
        if rows:
            return rows[0]
        draft = await self.get(user_id)
        if draft is None:
            raise RuntimeError("Unable to save onboarding draft")
        return draft

    async def claim_workspace_id(self, user_id: UUID) -> UUID:
        response = await execute(
            self.db.rpc("claim_onboarding_workspace", {"p_user_id": str(user_id)})
        )
        value = response.data
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            value = value.get("claim_onboarding_workspace") or value.get("workspace_id")
        if not value:
            raise RuntimeError("Unable to reserve onboarding workspace")
        return UUID(str(value))

    async def mark_completed(self, user_id: UUID, workspace_id: UUID) -> None:
        await execute(
            self.db.table("onboarding_drafts").update({"completed": True, "workspace_id": str(workspace_id), "updated_at": datetime.now(UTC).isoformat()}).eq("user_id", str(user_id))
        )
