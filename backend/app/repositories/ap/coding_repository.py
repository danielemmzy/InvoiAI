import asyncio
from datetime import UTC, datetime
from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.coding_mapper import InvoiceCodingMapper, CodingRuleMapper
from app.models.domain.ap import InvoiceCoding, CodingRule
from app.core.db import execute
class InvoiceCodingRepository(BaseRepository):
    table_name="invoice_codings"; mapper=InvoiceCodingMapper
    async def list_by_document(self, document_id: UUID):
        return self._many(await execute(self.table().select("*").eq("document_id", str(document_id)).order("created_at")))
    async def save_coding(self, coding: InvoiceCoding):
        payload=InvoiceCodingMapper.to_insert(coding)
        existing=await execute(self.table().select("id").eq("document_id", str(coding.document_id)).eq("line_item_id", str(coding.line_item_id) if coding.line_item_id else "00000000-0000-0000-0000-000000000000").limit(1))
        if existing.data:
            # Preserve the existing row identity and creation timestamp on retry.
            payload.pop("id", None)
            payload.pop("created_at", None)
            result=await execute(self.table().update(payload | {"updated_at":datetime.now(UTC).isoformat()}).eq("id", existing.data[0]["id"]))
        else:
            result=await execute(self.table().insert(payload))
        return self._one(result)
    async def save_codings(self, codings: list[InvoiceCoding]) -> list[InvoiceCoding]:
        """Persist a document's codings in two batch round trips.

        Previously each coding cost a SELECT plus an INSERT/UPDATE inside the
        caller's loop, so a 20-line invoice issued ~40 queries. Now existing
        rows are read once, new rows are inserted in a single statement, and
        only genuine updates run individually (they carry different values).
        """
        if not codings:
            return []

        document_id = str(codings[0].document_id)
        existing = (
            await execute(
                self.table()
                .select("id,line_item_id")
                .eq("document_id", document_id)
            )
        ).data or []
        existing_by_line = {
            str(row.get("line_item_id")): row["id"]
            for row in existing
            if row.get("line_item_id")
        }

        inserts: list[dict] = []
        updates: list[tuple[str, dict]] = []
        for coding in codings:
            payload = InvoiceCodingMapper.to_insert(coding)
            existing_id = existing_by_line.get(str(coding.line_item_id))
            if existing_id:
                # Preserve the existing row identity and creation timestamp on retry.
                payload.pop("id", None)
                payload.pop("created_at", None)
                updates.append((existing_id, payload | {"updated_at": datetime.now(UTC).isoformat()}))
            else:
                inserts.append(payload)

        saved: list[InvoiceCoding] = []
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

    async def approve_document(self, document_id: UUID, approved_by: UUID):
        await execute(self.table().update({"status":"approved","approved_by":str(approved_by),"updated_at":datetime.now(UTC).isoformat()}).eq("document_id",str(document_id)))
    async def historical_match(self, org_id: UUID, vendor_id: UUID | None, description: str | None):
        q=self.table().select("*, chart_of_accounts:gl_account_id(id,account_code,account_name,account_type)").eq("org_id",str(org_id)).not_.is_("gl_account_id","null").limit(50)
        if vendor_id and description:
            # Historical match is finalized by the service against document data; keep query bounded.
            return (await execute(q)).data or []
        return []
def _is_missing_rpc(exc: Exception) -> bool:
    """True when PostgREST reported that the database function does not exist."""
    if getattr(exc, "code", None) == "PGRST202":
        return True
    message = str(getattr(exc, "message", None) or exc).lower()
    return "could not find the function" in message or (
        "function" in message and "does not exist" in message
    )


class CodingRuleRepository(BaseRepository):
    table_name="coding_rules"; mapper=CodingRuleMapper
    async def list_active(self, org_id: UUID):
        return self._many(await execute(self.table().select("*").eq("org_id",str(org_id)).eq("is_active",True).order("priority")))
    async def increment_match_count(self, rule_id: UUID):
        await execute(self.db.rpc("increment_coding_rule_match", {"rule_id":str(rule_id)}))

    async def increment_match_counts(self, rule_ids: list[UUID]) -> None:
        """Apply every match count for one coding pass in a single call.

        Counts are aggregated per rule and incremented inside the database, so
        concurrent documents still add to the same counter atomically. If the
        batched function has not been deployed yet, fall back to one atomic
        single-rule RPC per distinct rule instead of one per line.
        """
        counts: dict[str, int] = {}
        for rule_id in rule_ids:
            key = str(rule_id)
            counts[key] = counts.get(key, 0) + 1
        if not counts:
            return

        payload = [{"rule_id": rule_id, "count": count} for rule_id, count in counts.items()]
        try:
            await execute(self.db.rpc("increment_coding_rule_matches", {"p_counts": payload}))
            return
        except Exception as exc:  # noqa: BLE001 - only function-missing errors are softened
            if not _is_missing_rpc(exc):
                raise

        await asyncio.gather(
            *(self.increment_match_count(UUID(rule_id)) for rule_id in counts)
        )
