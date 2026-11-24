import asyncio
from datetime import UTC, datetime
from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.workflow_engine_mapper import PaymentAuthorizationMapper
from app.models.domain.ap import PaymentAuthorization
from app.core.db import execute

class PaymentAuthorizationRepository(BaseRepository):
    table_name = "payment_authorizations"
    mapper = PaymentAuthorizationMapper

    async def get_by_document(self, org_id: UUID, document_id: UUID):
        response = (
            await execute(self.table().select("*").eq("org_id", str(org_id)).eq("document_id", str(document_id)).limit(1))
        )
        return self._one(response)

    async def list_by_documents(self, org_id: UUID, document_ids: list[str]):
        """Return every authorization for the given documents in one query."""
        if not document_ids:
            return []
        return self._many(await execute(
            self.table().select("*").eq("org_id", str(org_id)).in_("document_id", document_ids)
        ))

    async def upsert_many(self, org_id: UUID, items: list[tuple[str, dict]]):
        """Upsert several documents' authorizations with two batch round trips.

        ``items`` is a list of ``(document_id, payload)`` pairs. Existing rows
        are read once, new rows are inserted in a single statement, and only
        genuine updates run individually because their payloads differ.
        """
        if not items:
            return []
        document_ids = [document_id for document_id, _ in items]
        existing = (
            await execute(
                self.table().select("id,document_id").eq("org_id", str(org_id)).in_("document_id", document_ids)
            )
        ).data or []
        existing_by_doc = {str(row.get("document_id")): row["id"] for row in existing}
        now = datetime.now(UTC).isoformat()

        inserts: list[dict] = []
        updates: list[tuple[str, dict]] = []
        for document_id, payload in items:
            row = {**payload, "updated_at": now}
            existing_id = existing_by_doc.get(str(document_id))
            if existing_id:
                updates.append((existing_id, row))
            else:
                inserts.append({**row, "org_id": str(org_id), "document_id": str(document_id)})

        saved: list[PaymentAuthorization] = []
        if inserts:
            saved.extend(self._many(await execute(self.table().insert(inserts))))
        if updates:
            responses = await asyncio.gather(
                *(
                    execute(self.table().update(payload).eq("id", row_id).eq("org_id", str(org_id)))
                    for row_id, payload in updates
                )
            )
            saved.extend(self._one(response) for response in responses)
        return [row for row in saved if row is not None]

    async def list_by_status(self, org_id: UUID, status: str):
        return self._many(await execute(
            self.table().select("*").eq("org_id", str(org_id)).eq("status", status)
            .order("created_at", desc=True)
        ))

    async def upsert(self, org_id: UUID, document_id: UUID, data: dict):
        existing = await self.get_by_document(org_id, document_id)
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        if existing is None:
            payload.update({"org_id": str(org_id), "document_id": str(document_id)})
            return self._one(await execute(self.table().insert(payload)))
        return self._one(
            await execute(self.table().update(payload).eq("id", str(existing.id)).eq("org_id", str(org_id)))
        )
