"""
============================================================
Payment Mapper

Maps payment database rows to domain models.

============================================================
"""

from __future__ import annotations

from app.mappers.base import BaseMapper

from app.models.domain.payment import Payment


class PaymentMapper(BaseMapper):
    """
    Payment mapper.
    """

    domain_model = Payment

    # Until you expose payment API schemas,
    # use the domain model as the response model.

    response_model = Payment