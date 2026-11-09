from datetime import UTC, datetime
from uuid import UUID

from app.repositories.base import BaseRepository
from app.mappers.ap.workflow_engine_mapper import VendorDocumentRequestMapper


class VendorDocumentRequestRepository(BaseRepository):
    table_name = "vendor_document_requests"
    mapper = VendorDocumentRequestMapper

    async def get_by_token(self, token: str):
        response = self.table().select("*").eq("token", token).limit(1).execute()
        return self._one(response)

    async def list_for_vendor(self, org_id: UUID, vendor_id: UUID):
        return self._many(
            self.table().select("*").eq("org_id", str(org_id)).eq("vendor_id", str(vendor_id))
            .order("requested_at", desc=True).execute()
        )

    async def create_request(self, data: dict):
        return await self.create(data)

    async def update_status(self, request_id: UUID, data: dict):
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        return await self.update(request_id, payload)
