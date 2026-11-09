from datetime import UTC, datetime
from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.workflow_engine_mapper import PaymentAuthorizationMapper
from app.models.domain.ap import PaymentAuthorization

class PaymentAuthorizationRepository(BaseRepository):
    table_name = "payment_authorizations"
    mapper = PaymentAuthorizationMapper

    async def get_by_document(self, org_id: UUID, document_id: UUID):
        response = (
            self.table().select("*").eq("org_id", str(org_id)).eq("document_id", str(document_id)).limit(1).execute()
        )
        return self._one(response)

    async def list_by_status(self, org_id: UUID, status: str):
        return self._many(
            self.table().select("*").eq("org_id", str(org_id)).eq("status", status)
            .order("created_at", desc=True).execute()
        )

    async def upsert(self, org_id: UUID, document_id: UUID, data: dict):
        existing = await self.get_by_document(org_id, document_id)
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        if existing is None:
            payload.update({"org_id": str(org_id), "document_id": str(document_id)})
            return self._one(self.table().insert(payload).execute())
        return self._one(
            self.table().update(payload).eq("id", str(existing.id)).eq("org_id", str(org_id)).execute()
        )
