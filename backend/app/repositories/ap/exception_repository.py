from datetime import UTC, datetime
from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.exception_mapper import InvoiceExceptionMapper
from app.models.domain.ap import InvoiceException
class InvoiceExceptionRepository(BaseRepository):
    table_name="invoice_exceptions"; mapper=InvoiceExceptionMapper
    async def list_open(self, org_id: UUID):
        return self._many(self.table().select("*").eq("org_id",str(org_id)).in_("status",["open","in_review","escalated"]).order("created_at",desc=True).execute())
    async def list_by_document(self, org_id: UUID, document_id: UUID):
        return self._many(self.table().select("*").eq("org_id",str(org_id)).eq("document_id",str(document_id)).order("created_at",desc=True).execute())
    async def create_exception(self, exc: InvoiceException): return await self.create(exc)

    async def upsert_open(self, exc: InvoiceException):
        """Create the exception, or refresh an equivalent open one.

        Matching is retried after crashes and after a reviewer resolves a
        different exception. Re-running it must not create a second copy of the
        same price/quantity/missing-PO finding.
        """
        exception_type = getattr(exc.exception_type, "value", exc.exception_type)
        existing = (
            self.table()
            .select("id")
            .eq("org_id", str(exc.org_id))
            .eq("document_id", str(exc.document_id))
            .eq("exception_type", str(exception_type))
            .in_("status", ["open", "in_review", "escalated"])
            .limit(1)
            .execute()
        )
        if not existing.data:
            return await self.create(exc)

        payload = InvoiceExceptionMapper.to_insert(exc)
        payload.pop("id", None)
        payload.pop("created_at", None)
        # Preserve a reviewer's in-progress status and all resolution fields.
        payload.pop("status", None)
        payload["updated_at"] = datetime.now(UTC).isoformat()
        return self._one(
            self.table()
            .update(payload)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    async def resolve(self, org_id: UUID, exception_id: UUID, user_id: UUID, note: str, status: str="resolved"):
        return self.table().update({"status":status,"resolved_by":str(user_id),"resolved_at":datetime.now(UTC).isoformat(),"resolution_note":note,"updated_at":datetime.now(UTC).isoformat()}).eq("id",str(exception_id)).eq("org_id",str(org_id)).execute()
