"""Pure payment-instruction transition policy (no database/provider dependencies)."""
from app.core.enum.ap import PaymentInstructionStatus

ALLOWED_TRANSITIONS: dict[PaymentInstructionStatus, set[PaymentInstructionStatus]] = {
    PaymentInstructionStatus.REQUESTED: {PaymentInstructionStatus.PENDING_APPROVAL, PaymentInstructionStatus.SCHEDULED, PaymentInstructionStatus.APPROVED_FOR_PAYMENT, PaymentInstructionStatus.CANCELLED, PaymentInstructionStatus.BLOCKED},
    PaymentInstructionStatus.SCHEDULED: {PaymentInstructionStatus.AUTHORIZED, PaymentInstructionStatus.CANCELLED, PaymentInstructionStatus.BLOCKED},
    PaymentInstructionStatus.PENDING_APPROVAL: {PaymentInstructionStatus.APPROVED_FOR_PAYMENT, PaymentInstructionStatus.CANCELLED, PaymentInstructionStatus.BLOCKED},
    PaymentInstructionStatus.APPROVED_FOR_PAYMENT: {PaymentInstructionStatus.AUTHORIZED, PaymentInstructionStatus.SCHEDULED, PaymentInstructionStatus.BLOCKED, PaymentInstructionStatus.CANCELLED},
    PaymentInstructionStatus.PENDING_AUTHORIZATION: {PaymentInstructionStatus.AUTHORIZED, PaymentInstructionStatus.BLOCKED, PaymentInstructionStatus.CANCELLED},
    PaymentInstructionStatus.AUTHORIZED: {PaymentInstructionStatus.PROCESSING, PaymentInstructionStatus.BLOCKED, PaymentInstructionStatus.CANCELLED},
    PaymentInstructionStatus.PROCESSING: {PaymentInstructionStatus.PAID, PaymentInstructionStatus.FAILED, PaymentInstructionStatus.RETURNED, PaymentInstructionStatus.CANCELLED},
    PaymentInstructionStatus.PAID: {PaymentInstructionStatus.RECONCILED, PaymentInstructionStatus.RETURNED},
    PaymentInstructionStatus.FAILED: set(),
    PaymentInstructionStatus.RETURNED: set(),
    PaymentInstructionStatus.CANCELLED: set(),
    PaymentInstructionStatus.BLOCKED: {PaymentInstructionStatus.AUTHORIZED, PaymentInstructionStatus.CANCELLED},
    PaymentInstructionStatus.RECONCILED: set(),
}


def validate_transition(current: PaymentInstructionStatus, target: PaymentInstructionStatus) -> None:
    if current == target:
        return
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid payment status transition: {current.value} → {target.value}.")
