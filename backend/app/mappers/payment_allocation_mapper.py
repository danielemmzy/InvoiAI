from __future__ import annotations

from app.mappers.base import BaseMapper
from app.models.domain.payment_allocation import PaymentAllocation
from app.schemas.payment_allocation import (
    PaymentAllocationResponse,
)


class PaymentAllocationMapper(
    BaseMapper[
        PaymentAllocation,
        PaymentAllocationResponse,
    ]
):

    domain_model = PaymentAllocation

    response_model = PaymentAllocationResponse