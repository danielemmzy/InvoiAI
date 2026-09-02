from __future__ import annotations

from app.mappers.base import BaseMapper
from app.models.domain.stripe_event import StripeEvent


class StripeEventMapper(BaseMapper[StripeEvent, StripeEvent]):
    domain_model = StripeEvent
    response_model = StripeEvent
