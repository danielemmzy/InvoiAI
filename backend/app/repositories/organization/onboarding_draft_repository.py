from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase


class OnboardingDraftRepository:
    """Persistence for the single resumable draft owned by each user."""

    def __init__(self) -> None:
        self.db = get_supabase()

    def get(self, user_id: UUID) -> dict[str, Any] | None:
        response = self.db.table("onboarding_drafts").select("*").eq("user_id", str(user_id)).limit(1).execute()
        rows = response.data or []
        return rows[0] if rows else None

    def save(self, user_id: UUID, *, step: int, data: dict[str, Any]) -> dict[str, Any]:
        existing = self.get(user_id)
        table = self.db.table("onboarding_drafts")
        if existing:
            response = table.update({"step": step, "data": data, "updated_at": datetime.now(UTC).isoformat()}).eq("user_id", str(user_id)).execute()
        else:
            try:
                response = table.insert({"user_id": str(user_id), "step": step, "data": data}).execute()
            except Exception:
                # Concurrent first saves can race the one-draft-per-user unique key.
                if self.get(user_id) is None:
                    raise
                response = table.update({"step": step, "data": data, "updated_at": datetime.now(UTC).isoformat()}).eq("user_id", str(user_id)).execute()
        rows = response.data or []
        if rows:
            return rows[0]
        draft = self.get(user_id)
        if draft is None:
            raise RuntimeError("Unable to save onboarding draft")
        return draft

    def claim_workspace_id(self, user_id: UUID) -> UUID:
        response = self.db.rpc("claim_onboarding_workspace", {"p_user_id": str(user_id)}).execute()
        value = response.data
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            value = value.get("claim_onboarding_workspace") or value.get("workspace_id")
        if not value:
            raise RuntimeError("Unable to reserve onboarding workspace")
        return UUID(str(value))

    def mark_completed(self, user_id: UUID, workspace_id: UUID) -> None:
        self.db.table("onboarding_drafts").update({"completed": True, "workspace_id": str(workspace_id), "updated_at": datetime.now(UTC).isoformat()}).eq("user_id", str(user_id)).execute()
