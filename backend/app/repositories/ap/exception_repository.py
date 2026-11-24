import asyncio
from datetime import UTC, datetime
from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.exception_mapper import InvoiceExceptionMapper
from app.models.domain.ap import InvoiceException
from app.core.db import execute
class InvoiceExceptionRepository(BaseRepository):
    table_name="invoice_exceptions"; mapper=InvoiceExceptionMapper
    async def list_open(self, org_id: UUID):
        return self._many(await execute(self.table().select("*").eq("org_id",str(org_id)).in_("status",["open","in_review","escalated"]).order("created_at",desc=True)))
    async def list_by_document(self, org_id: UUID, document_id: UUID):
        return self._many(await execute(self.table().select("*").eq("org_id",str(org_id)).eq("document_id",str(document_id)).order("created_at",desc=True)))
    async def create_exception(self, exc: InvoiceException): return await self.create(exc)

    async def upsert_open(self, exc: InvoiceException):
        """Create the exception, or refresh an equivalent open one.

        Matching is retried after crashes and after a reviewer resolves a
        different exception. Re-running it must not create a second copy of the
        same price/quantity/missing-PO finding.
        """
        exception_type = getattr(exc.exception_type, "value", exc.exception_type)
        existing = await execute(
            self.table()
            .select("id")
            .eq("org_id", str(exc.org_id))
            .eq("document_id", str(exc.document_id))
            .eq("exception_type", str(exception_type))
            .in_("status", ["open", "in_review", "escalated"])
            .limit(1)
        )
        if not existing.data:
            return await self.create(exc)

        payload = InvoiceExceptionMapper.to_insert(exc)
        payload.pop("id", None)
        payload.pop("created_at", None)
        # Preserve a reviewer's in-progress status and all resolution fields.
        payload.pop("status", None)
        payload["updated_at"] = datetime.now(UTC).isoformat()
        return self._one(await execute(
            self.table()
            .update(payload)
            .eq("id", existing.data[0]["id"])
        ))
    async def upsert_open_many(self, exceptions: list[InvoiceException]) -> list[InvoiceException]:
        """Upsert a document's match exceptions in two batch round trips.

        The single-row helper costs a SELECT plus a write per exception. A
        document with several findings used to issue 2N queries; this reads the
        existing open rows once, inserts new findings in one statement, and only
        refreshes genuinely existing rows individually.
        """
        if not exceptions:
            return []

        org_id = str(exceptions[0].org_id)
        document_id = str(exceptions[0].document_id)
        existing = (
            await execute(
                self.table()
                .select("id,exception_type")
                .eq("org_id", org_id)
                .eq("document_id", document_id)
                .in_("status", ["open", "in_review", "escalated"])
            )
        ).data or []
        existing_by_type = {
            str(row.get("exception_type")): row["id"] for row in existing
        }

        inserts: list[dict] = []
        updates: list[tuple[str, dict]] = []
        now = datetime.now(UTC).isoformat()
        for exc in exceptions:
            exception_type = getattr(exc.exception_type, "value", exc.exception_type)
            existing_id = existing_by_type.get(str(exception_type))
            payload = InvoiceExceptionMapper.to_insert(exc)
            payload.pop("id", None)
            payload.pop("created_at", None)
            if existing_id:
                # Preserve a reviewer's in-progress status and resolution fields.
                payload.pop("status", None)
                payload["updated_at"] = now
                updates.append((existing_id, payload))
            else:
                inserts.append(payload)

        saved: list[InvoiceException] = []
        if inserts:
            saved.extend(self._many(await execute(self.table().insert(inserts))))
        if updates:
            responses = await asyncio.gather(
                *(
                    execute(self.table().update(payload).eq("id", row_id))
                    for row_id, payload in updates
                )
            )
            saved.extend(self._one(response) for response in responses)
        return [row for row in saved if row is not None]

    async def resolve(self, org_id: UUID, exception_id: UUID, user_id: UUID, note: str, status: str="resolved"):
        return await execute(self.table().update({"status":status,"resolved_by":str(user_id),"resolved_at":datetime.now(UTC).isoformat(),"resolution_note":note,"updated_at":datetime.now(UTC).isoformat()}).eq("id",str(exception_id)).eq("org_id",str(org_id)))
