"""
============================================================
Payment Instruction Service

Owns the payment_instructions lifecycle end to end:

  REQUESTED -> PENDING_APPROVAL -> APPROVED_FOR_PAYMENT
    -> PENDING_AUTHORIZATION -> AUTHORIZED -> PROCESSING
    -> PAID -> RECONCILED
  (BLOCKED / FAILED / CANCELLED are terminal-ish off-ramps)

Every transition is written to payment_instruction_events
(immutable audit trail) — this is the payment-side equivalent
of approval_history for bill approvals. The document's own
ap_status only moves PAYMENT_READY -> PAID -> RECONCILED, via
InvoiceStateMachine, once the provider confirms success — it is
never set to PAID just because a payment was requested.

Provider access always goes through the PaymentProvider
interface (app/services/payment/provider/base.py); this service
never hardcodes a provider or talks to a payment rail's SDK
directly.
============================================================
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.enum.ap import InvoiceAPStatus, PaymentInstructionStatus
from app.core.config import settings
from app.core.supabase import get_supabase
from app.models.domain.ap import PaymentInstruction
from app.repositories.ap.payment_instruction_repository import (
    PaymentInstructionEventRepository,
    PaymentInstructionRepository,
)
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.services.payment.provider.base import PaymentProvider
from app.services.payment.provider.mock_provider import MockPaymentProvider
from app.services.payment.payment_state_machine import validate_transition

# Process-wide mock provider instance so idempotency-key lookups within
# a single running process actually find prior "payments". A real
# provider integration replaces this with a real HTTP client and does
# not need process-local state.
_DEFAULT_PROVIDER = MockPaymentProvider()


from app.core.db import execute

class PaymentInstructionService:



    def __init__(
        self,
        db=None,
        repository: PaymentInstructionRepository | None = None,
        events: PaymentInstructionEventRepository | None = None,
        state_machine: InvoiceStateMachine | None = None,
        provider: PaymentProvider | None = None,
    ) -> None:
        self.db = db or get_supabase()
        self.repository = repository or PaymentInstructionRepository()
        self.events = events or PaymentInstructionEventRepository()
        self.state_machine = state_machine or InvoiceStateMachine(self.db)
        self.provider = provider or _DEFAULT_PROVIDER

    # =========================================================
    # Create
    # =========================================================

    async def get_or_create(
        self,
        *,
        org_id: UUID,
        document_id: UUID,
        requested_by: UUID | None,
        idempotency_key: str | None = None,
        payment_method: str | None = None,
        scheduled_date: str | None = None,
    ) -> PaymentInstruction:

        key = (idempotency_key or f"doc:{document_id}").strip()
        if not key or len(key) > 200:
            raise ValueError("An idempotency key of 1–200 characters is required.")
        if scheduled_date:
            try:
                parsed_date = date.fromisoformat(scheduled_date)
            except ValueError as exc:
                raise ValueError("Scheduled date must be a valid ISO date (YYYY-MM-DD).") from exc
            if parsed_date < datetime.now(UTC).date():
                raise ValueError("Scheduled date cannot be in the past.")

        existing = await self.repository.get_by_idempotency_key(org_id, key)
        if existing is not None:
            if str(existing.document_id) != str(document_id):
                raise ValueError("This idempotency key is already associated with a different bill.")
            return existing

        doc = (
            (await execute(self.db.table("documents").select("total_amount,currency,vendor_id,ap_status")
            .eq("org_id", str(org_id)).eq("id", str(document_id)).limit(1))).data
        )
        if not doc:
            raise ValueError(f"Document {document_id} was not found.")
        doc = doc[0]
        if doc.get("ap_status") != InvoiceAPStatus.PAYMENT_READY.value:
            raise ValueError("Only bills approved and marked ready for payment can enter the payment workflow.")
        amount = Decimal(str(doc.get("total_amount") or 0))
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        payload = {
            "org_id": str(org_id),
            "document_id": str(document_id),
            "vendor_id": doc.get("vendor_id"),
            "amount": str(amount),
            "currency": doc.get("currency") or "USD",
            "payment_method": payment_method,
            "scheduled_date": scheduled_date,
            "requested_by": str(requested_by) if requested_by else None,
            "idempotency_key": key,
            "status": PaymentInstructionStatus.REQUESTED.value,
        }

        created = await self.repository.create_instruction(payload)
        if created is None:
            raise RuntimeError("Failed to create payment instruction.")

        await self._record_event(org_id=org_id, instruction_id=created.id, from_status=None, to_status=created.status, actor_id=requested_by, reason="created")
        return created

    # =========================================================
    # Transitions
    # =========================================================

    async def transition(
        self,
        *,
        org_id: UUID,
        instruction_id: UUID,
        to_status: PaymentInstructionStatus,
        actor_id: UUID | None = None,
        reason: str | None = None,
        **extra_fields: Any,
    ) -> PaymentInstruction:

        current = await self.repository.get(instruction_id)
        if current is None or str(current.org_id) != str(org_id):
            raise ValueError("Payment instruction not found.")
        try:
            current_status = PaymentInstructionStatus(current.status)
        except ValueError as exc:
            raise ValueError(f"Unknown current payment status: {current.status}") from exc
        if current_status == to_status:
            return current
        validate_transition(current_status, to_status)

        atomic_transition = getattr(self.repository, "transition_with_event", None)
        if callable(atomic_transition):
            updated = await atomic_transition(
                org_id=org_id, instruction_id=instruction_id,
                expected_status=current_status.value, status=to_status.value,
                actor_id=actor_id, reason=reason, fields=extra_fields,
            )
            if updated is None:
                raise ValueError("Payment status changed concurrently; refresh payment activity before retrying.")
            return updated

        # Dependency-injected test doubles / older adapters use the compatibility path.
        updated = await self.repository.update_status(instruction_id, to_status.value, org_id=org_id, **extra_fields)
        if updated is None:
            raise RuntimeError(f"Failed to transition payment instruction {instruction_id}.")
        await self._record_event(
            org_id=org_id, instruction_id=instruction_id,
            from_status=current.status, to_status=to_status.value,
            actor_id=actor_id, reason=reason, metadata=extra_fields,
        )
        return updated

    async def _record_event(self, *, org_id: UUID, instruction_id: UUID, from_status: str | None, to_status: str, actor_id: UUID | None, reason: str | None, metadata: dict | None = None) -> None:
        await self.events.record({
            "org_id": str(org_id),
            "payment_instruction_id": str(instruction_id),
            "from_status": from_status,
            "to_status": to_status,
            "actor_id": str(actor_id) if actor_id else None,
            "reason": reason,
            "metadata": metadata or {},
        })

    # =========================================================
    # Provider orchestration
    # =========================================================

    async def execute(self, *, org_id: UUID, instruction_id: UUID, actor_id: UUID | None) -> PaymentInstruction:
        """
        Called once an instruction is AUTHORIZED. Creates the payment
        with the provider and moves the instruction to PROCESSING.
        Never marks PAID here — that only happens on provider
        confirmation via handle_webhook()/reconcile().
        """

        instruction = await self.repository.get(instruction_id)
        if instruction is None or str(instruction.org_id) != str(org_id):
            raise ValueError("Payment instruction not found.")

        if instruction.status != PaymentInstructionStatus.AUTHORIZED:
            raise ValueError(f"Payment instruction must be AUTHORIZED before execution (currently {instruction.status}).")
        if self.provider.name == "mock" and settings.environment.strip().lower() not in {"development", "dev", "test", "testing"}:
            raise ValueError("Mock payments are disabled outside development. Configure a real payment provider before releasing funds.")

        result = await self.provider.create_payment(
            idempotency_key=instruction.idempotency_key,
            amount=instruction.amount,
            currency=instruction.currency,
            vendor_id=instruction.vendor_id,
            payment_method=instruction.payment_method,
            metadata={"document_id": str(instruction.document_id), "org_id": str(org_id)},
        )

        return await self.transition(
            org_id=org_id, instruction_id=instruction_id,
            to_status=PaymentInstructionStatus.PROCESSING,
            actor_id=actor_id, reason="submitted to provider",
            provider=self.provider.name, provider_payment_id=result.provider_payment_id,
        )

    async def cancel(self, *, org_id: UUID, instruction_id: UUID, actor_id: UUID | None, reason: str) -> PaymentInstruction:
        if not reason or not reason.strip():
            raise ValueError("A cancellation reason is required.")
        instruction = await self.repository.get(instruction_id)
        if instruction is None or str(instruction.org_id) != str(org_id):
            raise ValueError("Payment instruction not found.")
        if instruction.status in {PaymentInstructionStatus.PAID, PaymentInstructionStatus.RECONCILED, PaymentInstructionStatus.FAILED, PaymentInstructionStatus.RETURNED, PaymentInstructionStatus.CANCELLED}:
            raise ValueError(f"A payment in {instruction.status.value} status cannot be cancelled.")
        if instruction.status == PaymentInstructionStatus.PROCESSING:
            if not instruction.provider_payment_id:
                raise ValueError("Processing payment has no provider reference; cancellation cannot be confirmed.")
            result = await self.provider.cancel_payment(
                provider_payment_id=instruction.provider_payment_id, reason=reason.strip()
            )
            if (result.status or "").lower() not in {"cancelled", "canceled", "voided"}:
                raise ValueError("The provider has not confirmed cancellation. Refresh payment status before retrying.")
        return await self.transition(
            org_id=org_id, instruction_id=instruction_id,
            to_status=PaymentInstructionStatus.CANCELLED, actor_id=actor_id,
            reason=reason.strip(),
        )

    async def handle_webhook(self, *, org_id: UUID, payload: dict[str, Any], headers: dict[str, str]) -> PaymentInstruction:

        event = await self.provider.handle_webhook(payload=payload, headers=headers)

        rows = (
            (await execute(self.db.table("payment_instructions").select("id,document_id,status")
            .eq("org_id", str(org_id)).eq("provider_payment_id", event.provider_payment_id)
            .limit(1))).data
        )
        if not rows:
            raise ValueError(f"No payment instruction found for provider payment {event.provider_payment_id}.")

        instruction_id = UUID(rows[0]["id"])
        document_id = UUID(rows[0]["document_id"])

        normalized_status = (event.status or "").strip().lower()
        if normalized_status in {"paid", "completed", "succeeded", "settled"}:
            current = await self.repository.get(instruction_id)
            if current and current.status in {PaymentInstructionStatus.PAID, PaymentInstructionStatus.RECONCILED}:
                return current
            updated = await self.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.PAID, reason="provider webhook: paid",
            )
            await self.state_machine.transition(
                document_id, org_id, InvoiceAPStatus.PAID,
                triggered_by="payment_webhook", reason=f"provider={self.provider.name}",
            )
            return updated

        if normalized_status in {"failed", "denied", "cancelled", "canceled", "returned", "reversed"}:
            current = await self.repository.get(instruction_id)
            if current and current.status in {PaymentInstructionStatus.FAILED, PaymentInstructionStatus.CANCELLED, PaymentInstructionStatus.RETURNED}:
                return current
            target_status = (
                PaymentInstructionStatus.RETURNED
                if normalized_status in {"returned", "reversed"}
                else PaymentInstructionStatus.CANCELLED
                if normalized_status in {"cancelled", "canceled"}
                else PaymentInstructionStatus.FAILED
            )
            updated = await self.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=target_status, reason=event.failure_reason or f"provider webhook: {normalized_status}",
                failure_reason=event.failure_reason,
            )
            if target_status == PaymentInstructionStatus.RETURNED:
                document = (await execute(self.db.table("documents").select("ap_status").eq(
                    "org_id", str(org_id)
                ).eq("id", str(document_id)).limit(1))).data or []
                if document and document[0].get("ap_status") in {InvoiceAPStatus.PAID.value, InvoiceAPStatus.RECONCILED.value}:
                    await self.state_machine.transition(
                        document_id, org_id, InvoiceAPStatus.PAYMENT_READY,
                        triggered_by="payment_return_webhook", reason=event.failure_reason or "Provider returned/reversed payment",
                        metadata={"provider": self.provider.name, "provider_payment_id": event.provider_payment_id},
                    )
            return updated

        # Any other provider status (processing, scheduled, etc.) — record
        # the event without forcing a status we don't have a clean mapping
        # for; the instruction's status only moves on paid/failed/reconcile.
        await self._record_event(org_id=org_id, instruction_id=instruction_id, from_status=rows[0]["status"], to_status=rows[0]["status"], actor_id=None, reason=f"provider webhook: {event.status}", metadata=event.raw)
        current = await self.repository.get(instruction_id)
        return current

    async def reconcile(self, *, org_id: UUID, instruction_id: UUID) -> PaymentInstruction:
        instruction = await self.repository.get(instruction_id)
        if instruction is None or str(instruction.org_id) != str(org_id):
            raise ValueError("Payment instruction not found.")

        if not instruction.provider_payment_id:
            raise ValueError("Payment instruction has no provider payment to reconcile.")

        result = await self.provider.reconcile(provider_payment_id=instruction.provider_payment_id)

        provider_status = (result.status or "").lower()
        if provider_status in {"paid", "completed", "succeeded", "settled"}:
            if instruction.status == PaymentInstructionStatus.RECONCILED:
                return instruction
            if instruction.status == PaymentInstructionStatus.PROCESSING:
                instruction = await self.transition(
                    org_id=org_id, instruction_id=instruction_id,
                    to_status=PaymentInstructionStatus.PAID, reason="provider status confirmed during reconciliation",
                )
                await self.state_machine.transition(
                    instruction.document_id, org_id, InvoiceAPStatus.PAID,
                    triggered_by="reconciliation", reason=f"provider={self.provider.name}",
                )
            if instruction.status == PaymentInstructionStatus.PAID:
                await self.state_machine.transition(
                    instruction.document_id, org_id, InvoiceAPStatus.RECONCILED,
                    triggered_by="reconciliation", reason=f"provider={self.provider.name}",
                )
                return await self.transition(
                    org_id=org_id, instruction_id=instruction_id,
                    to_status=PaymentInstructionStatus.RECONCILED, reason="reconciled against provider",
                )
            return instruction

        if provider_status in {"failed", "denied"} and instruction.status == PaymentInstructionStatus.PROCESSING:
            return await self.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.FAILED, reason="provider status confirmed during reconciliation",
                failure_reason=(result.raw or {}).get("failure_reason"),
            )
        if provider_status in {"returned", "reversed"} and instruction.status in {PaymentInstructionStatus.PROCESSING, PaymentInstructionStatus.PAID}:
            updated = await self.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.RETURNED, reason="provider reports returned/reversed payment",
                failure_reason=(result.raw or {}).get("failure_reason"),
            )
            document = (await execute(self.db.table("documents").select("ap_status").eq(
                "org_id", str(org_id)
            ).eq("id", str(instruction.document_id)).limit(1))).data or []
            if document and document[0].get("ap_status") in {InvoiceAPStatus.PAID.value, InvoiceAPStatus.RECONCILED.value}:
                await self.state_machine.transition(
                    instruction.document_id, org_id, InvoiceAPStatus.PAYMENT_READY,
                    triggered_by="payment_reconciliation", reason="Provider reports returned/reversed payment",
                    metadata={"provider": self.provider.name, "provider_payment_id": instruction.provider_payment_id},
                )
            return updated

        if provider_status in {"cancelled", "canceled", "voided"} and instruction.status in {
            PaymentInstructionStatus.PROCESSING, PaymentInstructionStatus.AUTHORIZED,
        }:
            return await self.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.CANCELLED,
                reason="provider confirms cancellation during reconciliation",
            )
        return instruction
