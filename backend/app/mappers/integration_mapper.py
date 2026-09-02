"""
============================================================
Integration Mapper

Converts between:

Database
↓
Domain

Domain
↓
Response
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.integration import (
    IntegrationConnection,
    IntegrationSync,
    IntegrationWebhook,
)

from app.schemas.integration import (
    IntegrationConnectionResponse,
    IntegrationSyncResponse,
    IntegrationWebhookResponse,
)


class IntegrationConnectionMapper(
    BaseMapper[
        IntegrationConnection,
        IntegrationConnectionResponse,
    ]
):
    domain_model = IntegrationConnection
    response_model = IntegrationConnectionResponse


class IntegrationSyncMapper(
    BaseMapper[
        IntegrationSync,
        IntegrationSyncResponse,
    ]
):
    domain_model = IntegrationSync
    response_model = IntegrationSyncResponse


class IntegrationWebhookMapper(
    BaseMapper[
        IntegrationWebhook,
        IntegrationWebhookResponse,
    ]
):
    domain_model = IntegrationWebhook
    response_model = IntegrationWebhookResponse