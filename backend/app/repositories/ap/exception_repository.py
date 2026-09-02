from datetime import UTC, datetime
from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.exception_mapper import InvoiceExceptionMapper
from app.models.domain.ap import InvoiceException
class InvoiceExceptionRepository(BaseRepository):
    table_name="invoice_exceptions"; mapper=InvoiceExceptionMapper
    async def list_open(self, org_id: UUID):
        return self._many(self.table().select("*").eq("org_id",str(org_id)).eq("status","open").order("created_at",desc=True).execute())
    async def list_by_document(self, org_id: UUID, document_id: UUID):
        return self._many(self.table().select("*").eq("org_id",str(org_id)).eq("document_id",str(document_id)).order("created_at",desc=True).execute())
    async def create_exception(self, exc: InvoiceException): return await self.create(exc)
    async def resolve(self, org_id: UUID, exception_id: UUID, user_id: UUID, note: str, status: str="resolved"):
        return self.table().update({"status":status,"resolved_by":str(user_id),"resolved_at":datetime.now(UTC).isoformat(),"resolution_note":note,"updated_at":datetime.now(UTC).isoformat()}).eq("id",str(exception_id)).eq("org_id",str(org_id)).execute()
