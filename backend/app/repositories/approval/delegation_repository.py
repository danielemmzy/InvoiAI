from __future__ import annotations
from datetime import UTC, datetime
from uuid import UUID
from app.core.supabase import get_supabase
from app.core.db import execute

class ApprovalDelegationRepository:
    table_name = "approval_delegations"
    def __init__(self, db=None): self.db = db or get_supabase()
    def _table(self): return self.db.table(self.table_name)
    async def list_active(self, org_id: UUID, now: datetime | None = None):
        now = now or datetime.now(UTC)
        rows = (await execute(self._table().select("*").eq("org_id", str(org_id)).is_("revoked_at", "null"))).data or []
        return [r for r in rows if datetime.fromisoformat(str(r["starts_at"]).replace("Z", "+00:00")) <= now <= datetime.fromisoformat(str(r["ends_at"]).replace("Z", "+00:00"))]
    async def create(self, org_id: UUID, data: dict):
        payload = {**data, "org_id": str(org_id)}
        return (await execute(self._table().insert(payload))).data[0]
    async def revoke(self, org_id: UUID, delegation_id: UUID):
        return (await execute(self._table().update({"revoked_at": datetime.now(UTC).isoformat()}).eq("id", str(delegation_id)).eq("org_id", str(org_id)))).data[0]
