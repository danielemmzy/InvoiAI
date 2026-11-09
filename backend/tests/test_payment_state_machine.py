import pytest

from app.core.enum.ap import PaymentInstructionStatus as S
from app.services.payment.payment_state_machine import validate_transition


@pytest.mark.parametrize(("current", "target"), [
    (S.REQUESTED, S.PENDING_APPROVAL),
    (S.PENDING_APPROVAL, S.APPROVED_FOR_PAYMENT),
    (S.APPROVED_FOR_PAYMENT, S.AUTHORIZED),
    (S.AUTHORIZED, S.PROCESSING),
    (S.PROCESSING, S.PAID),
    (S.PAID, S.RECONCILED),
    (S.PAID, S.RETURNED),
    (S.BLOCKED, S.AUTHORIZED),
    (S.REQUESTED, S.CANCELLED),
])
def test_allowed_payment_transitions(current, target):
    validate_transition(current, target)


@pytest.mark.parametrize(("current", "target"), [
    (S.REQUESTED, S.PAID),
    (S.PENDING_APPROVAL, S.PROCESSING),
    (S.PROCESSING, S.RECONCILED),
    (S.RECONCILED, S.PROCESSING),
    (S.FAILED, S.AUTHORIZED),
    (S.CANCELLED, S.PROCESSING),
])
def test_disallowed_payment_transitions(current, target):
    with pytest.raises(ValueError, match="Invalid payment status transition"):
        validate_transition(current, target)


def test_same_status_is_idempotent():
    validate_transition(S.PROCESSING, S.PROCESSING)
