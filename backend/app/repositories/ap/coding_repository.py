from datetime import UTC, datetime
from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.coding_mapper import InvoiceCodingMapper, CodingRuleMapper
from app.models.domain.ap import InvoiceCoding, CodingRule
class InvoiceCodingRepository(BaseRepository):
    table_name="invoice_codings"; mapper=InvoiceCodingMapper
    async def list_by_document(self, document_id: UUID):
        return self._many(self.table().select("*").eq("document_id", str(document_id)).order("created_at").execute())
    async def save_coding(self, coding: InvoiceCoding):
        payload=InvoiceCodingMapper.to_insert(coding)
        existing=self.table().select("id").eq("document_id", str(coding.document_id)).eq("line_item_id", str(coding.line_item_id) if coding.line_item_id else "00000000-0000-0000-0000-000000000000").limit(1).execute()
        if existing.data:
            result=self.table().update(payload | {"updated_at":datetime.now(UTC).isoformat()}).eq("id", existing.data[0]["id"]).execute()
        else:
            result=self.table().insert(payload).execute()
        return self._one(result)
    async def approve_document(self, document_id: UUID, approved_by: UUID):
        self.table().update({"status":"approved","approved_by":str(approved_by),"updated_at":datetime.now(UTC).isoformat()}).eq("document_id",str(document_id)).execute()
    async def historical_match(self, org_id: UUID, vendor_id: UUID | None, description: str | None):
        q=self.table().select("*, chart_of_accounts:gl_account_id(id,account_code,account_name,account_type)").eq("org_id",str(org_id)).not_.is_("gl_account_id","null").limit(50)
        if vendor_id and description:
            # Historical match is finalized by the service against document data; keep query bounded.
            return q.execute().data or []
        return []
class CodingRuleRepository(BaseRepository):
    table_name="coding_rules"; mapper=CodingRuleMapper
    async def list_active(self, org_id: UUID):
        return self._many(self.table().select("*").eq("org_id",str(org_id)).eq("is_active",True).order("priority").execute())
    async def increment_match_count(self, rule_id: UUID):
        self.db.rpc("increment_coding_rule_match", {"rule_id":str(rule_id)}).execute()
