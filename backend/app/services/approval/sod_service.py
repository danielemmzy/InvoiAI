from __future__ import annotations
from uuid import UUID
from app.core.supabase import get_supabase

class SegregationOfDutiesService:
    def __init__(self, db=None): self.db = db or get_supabase()

    async def enabled(self, org_id: UUID, rule_key: str) -> bool:
        rows = self.db.table("sod_rules").select("enabled").eq("org_id", str(org_id)).eq("rule_key", rule_key).limit(1).execute().data or []
        return bool(rows and rows[0].get("enabled", True))

    async def validate_invoice_approval(self, *, org_id: UUID, document_id: UUID, actor_id: UUID) -> None:
        doc = self.db.table("documents").select("created_by,ap_status").eq("org_id", str(org_id)).eq("id", str(document_id)).limit(1).execute().data or []
        if not doc: raise ValueError("Document not found.")
        if await self.enabled(org_id, "no_self_approval") and str(doc[0].get("created_by") or "") == str(actor_id):
            raise PermissionError("Segregation-of-duties policy prevents the requester from approving their own invoice.")
