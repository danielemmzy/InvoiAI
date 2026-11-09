from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.enum.ap import PaymentInstructionStatus as S
from app.models.domain.ap import PaymentInstruction
from app.services.payment.payment_instruction_service import PaymentInstructionService
from app.services.payment.provider.mock_provider import MockPaymentProvider


class FakeRepository:
    def __init__(self, current):
        self.current = current
        self.calls = []

    async def get(self, instruction_id):
        return self.current

    async def transition_with_event(self, **kwargs):
        self.calls.append(kwargs)
        self.current.status = S(kwargs["status"])
        return self.current


class FakeDB:
    pass


class ReadOnlyRepository:
    def __init__(self, instruction):
        self.instruction = instruction

    async def get(self, instruction_id):
        return self.instruction


@pytest.mark.asyncio
async def test_transition_uses_atomic_status_and_event_repository_method():
    org_id, document_id, instruction_id = uuid4(), uuid4(), uuid4()
    instruction = PaymentInstruction(
        id=instruction_id,
        org_id=org_id,
        document_id=document_id,
        amount="125.00",
        currency="USD",
        idempotency_key="payment-1",
        status=S.AUTHORIZED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository = FakeRepository(instruction)
    service = PaymentInstructionService(
        db=FakeDB(), repository=repository, events=object(), state_machine=object(), provider=object()
    )

    updated = await service.transition(
        org_id=org_id,
        instruction_id=instruction_id,
        to_status=S.PROCESSING,
        actor_id=None,
        reason="provider submission accepted",
        provider="test-provider",
        provider_payment_id="provider-ref-1",
    )

    assert updated.status == S.PROCESSING
    assert len(repository.calls) == 1
    assert repository.calls[0]["expected_status"] == S.AUTHORIZED.value
    assert repository.calls[0]["status"] == S.PROCESSING.value
    assert repository.calls[0]["fields"]["provider_payment_id"] == "provider-ref-1"


@pytest.mark.asyncio
async def test_transition_rejects_illegal_state_before_database_write():
    org_id, document_id, instruction_id = uuid4(), uuid4(), uuid4()
    instruction = PaymentInstruction(
        id=instruction_id,
        org_id=org_id,
        document_id=document_id,
        amount="125.00",
        currency="USD",
        idempotency_key="payment-2",
        status=S.REQUESTED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository = FakeRepository(instruction)
    service = PaymentInstructionService(
        db=FakeDB(), repository=repository, events=object(), state_machine=object(), provider=object()
    )

    with pytest.raises(ValueError, match="Invalid payment status transition"):
        await service.transition(
            org_id=org_id, instruction_id=instruction_id, to_status=S.PAID, actor_id=None, reason="bad transition"
        )
    assert repository.calls == []


@pytest.mark.asyncio
async def test_execute_rejects_mock_provider_outside_development(monkeypatch):
    """A production-like runtime must never release funds through the mock rail."""
    org_id, document_id, instruction_id = uuid4(), uuid4(), uuid4()
    instruction = PaymentInstruction(
        id=instruction_id,
        org_id=org_id,
        document_id=document_id,
        amount="125.00",
        currency="USD",
        idempotency_key="payment-mock-production",
        status=S.AUTHORIZED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    service = PaymentInstructionService(
        db=FakeDB(),
        repository=ReadOnlyRepository(instruction),
        events=object(),
        state_machine=object(),
        provider=MockPaymentProvider(),
    )
    monkeypatch.setattr("app.services.payment.payment_instruction_service.settings.environment", "production")

    with pytest.raises(ValueError, match="Mock payments are disabled"):
        await service.execute(org_id=org_id, instruction_id=instruction_id, actor_id=None)


@pytest.mark.asyncio
async def test_execute_rejects_mock_provider_in_production_even_when_debug_is_misconfigured(monkeypatch):
    org_id, document_id, instruction_id = uuid4(), uuid4(), uuid4()
    instruction = PaymentInstruction(
        id=instruction_id, org_id=org_id, document_id=document_id, amount="125.00", currency="USD",
        idempotency_key="payment-mock-production-debug", status=S.AUTHORIZED,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    service = PaymentInstructionService(
        db=FakeDB(), repository=ReadOnlyRepository(instruction), events=object(), state_machine=object(), provider=MockPaymentProvider(),
    )
    monkeypatch.setattr("app.services.payment.payment_instruction_service.settings.environment", "production")
    monkeypatch.setattr("app.services.payment.payment_instruction_service.settings.debug", True)

    with pytest.raises(ValueError, match="Mock payments are disabled"):
        await service.execute(org_id=org_id, instruction_id=instruction_id, actor_id=None)
