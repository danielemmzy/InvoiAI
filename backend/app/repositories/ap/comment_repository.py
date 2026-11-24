from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.workflow_engine_mapper import InvoiceCommentMapper
from app.models.domain.ap import InvoiceComment

class InvoiceCommentRepository(BaseRepository):
    table_name = "invoice_comments"
    mapper = InvoiceCommentMapper

    async def list_for_document(self, org_id: UUID, document_id: UUID):
        return self._many(await execute(
            self.table().select("*").eq("org_id", str(org_id)).eq("document_id", str(document_id))
            .order("created_at")
        ))

    async def create_comment(self, comment: InvoiceComment | dict):
        return await self.create(comment)
