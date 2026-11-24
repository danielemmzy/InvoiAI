from __future__ import annotations
from datetime import UTC, datetime
from uuid import UUID
from app.core.supabase import get_supabase
from app.core.db import execute

class ApprovalAuthorityRepository:
    table_name = "approval_authorities"
    def __init__(self, db=None):
        self.db = db or get_supabase()
    def _table(self): return self.db.table(self.table_name)

    async def list_for_member(self, org_id: UUID, membership_id: UUID, approval_type: str | None = None):
        q = self._table().select("*").eq("org_id", str(org_id)).eq("membership_id", str(membership_id)).eq("is_active", True)
        if approval_type: q = q.eq("approval_type", approval_type)
        return (await execute(q.order("limit_amount"))).data or []

    async def upsert(self, org_id: UUID, membership_id: UUID, data: dict):
        payload = {**data, "org_id": str(org_id), "membership_id": str(membership_id), "updated_at": datetime.now(UTC).isoformat()}
        return (await execute(self._table().upsert(payload, on_conflict="membership_id,approval_type,currency"))).data[0]

    async def deactivate(self, org_id: UUID, membership_id: UUID, approval_type: str):
        response = await execute(
            self._table()
            .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
            .eq("org_id", str(org_id))
            .eq("membership_id", str(membership_id))
            .eq("approval_type", approval_type)
        )
        return response.data or []

    async def active_for_member(self, org_id: UUID, membership_id: UUID, approval_type: str, currency: str, amount=None):
        rows = await self.list_for_member(org_id, membership_id, approval_type)
        now = datetime.now(UTC)
        currency = currency.upper()
        eligible = []
        for row in rows:
            if str(row.get("currency", "")).upper() != currency: continue
            start = row.get("effective_from")
            end = row.get("effective_until")
            if start and datetime.fromisoformat(str(start).replace("Z", "+00:00")) > now: continue
            if end and datetime.fromisoformat(str(end).replace("Z", "+00:00")) < now: continue
            if amount is not None and float(row.get("limit_amount") or 0) < float(amount): continue
            eligible.append(row)
        return max(eligible, key=lambda r: float(r.get("limit_amount") or 0), default=None)
