"""
============================================================
Subscription Mapper

Converts between

Database
↓
Domain

Domain
↓
Response
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.subscription import (
    Subscription,
)

from app.schemas.subscription import (
    SubscriptionResponse,
)


class SubscriptionMapper(
    BaseMapper[
        Subscription,
        SubscriptionResponse,
    ]
):
    """
    Mapper for subscriptions.
    """

    domain_model = Subscription

    response_model = SubscriptionResponse