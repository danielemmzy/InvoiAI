from datetime import UTC, datetime
from uuid import UUID

from app.repositories.base import BaseRepository
from app.mappers.ap.workflow_engine_mapper import PaymentInstructionMapper, PaymentInstructionEventMapper
from app.models.domain.ap import PaymentInstruction


class PaymentInstructionRepository(BaseRepository):
    table_name = "payment_instructions"
    mapper = PaymentInstructionMapper

    async def get_by_idempotency_key(self, org_id: UUID, idempotency_key: str) -> PaymentInstruction | None:
        response = (
            self.table().select("*").eq("org_id", str(org_id))
            .eq("idempotency_key", idempotency_key).limit(1).execute()
        )
        return self._one(response)

    async def list_for_document(self, org_id: UUID, document_id: UUID) -> list[PaymentInstruction]:
        return self._many(
            self.table().select("*").eq("org_id", str(org_id)).eq("document_id", str(document_id))
            .order("created_at", desc=True).execute()
        )

    async def list_by_status(self, org_id: UUID, status: str) -> list[PaymentInstruction]:
        return self._many(
            self.table().select("*").eq("org_id", str(org_id)).eq("status", status)
            .order("scheduled_date").execute()
        )

    async def create_instruction(self, data: PaymentInstruction | dict):
        return await self.create(data)

    async def transition_with_event(
        self, *, org_id: UUID, instruction_id: UUID, expected_status: str,
        status: str, actor_id: UUID | None, reason: str | None, fields: dict | None = None,
    ) -> PaymentInstruction | None:
        """Atomically update a payment status and append its audit event in PostgreSQL."""
        response = self.db.rpc("transition_payment_instruction_with_event", {
            "p_org_id": str(org_id),
            "p_instruction_id": str(instruction_id),
            "p_expected_status": expected_status,
            "p_to_status": status,
            "p_actor_id": str(actor_id) if actor_id else None,
            "p_reason": reason,
            "p_extra_fields": fields or {},
        }).execute()
        data = response.data
        if not data:
            return None
        row = data[0] if isinstance(data, list) else data
        if isinstance(row, dict) and "transition_payment_instruction_with_event" in row:
            row = row["transition_payment_instruction_with_event"]
        return self.mapper.to_domain(row) if isinstance(row, dict) else None

    async def update_status(self, instruction_id: UUID, status: str, *, org_id: UUID, **fields) -> PaymentInstruction | None:
        # Update with both primary key and tenant scope. BaseRepository.update
        # only filters by ID, which is insufficient for a money-moving record.
        payload = {"status": status, "updated_at": datetime.now(UTC).isoformat(), **fields}
        payload.pop("org_id", None)
        response = (
            self.table().update(payload)
            .eq("id", str(instruction_id)).eq("org_id", str(org_id))
            .execute()
        )
        return self._one(response)


class PaymentInstructionEventRepository(BaseRepository):
    table_name = "payment_instruction_events"
    mapper = PaymentInstructionEventMapper

    async def list_for_instruction(self, instruction_id: UUID):
        return self._many(
            self.table().select("*").eq("payment_instruction_id", str(instruction_id))
            .order("created_at").execute()
        )

    async def record(self, data: dict):
        return await self.create(data)
