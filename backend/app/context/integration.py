"""
============================================================
Integration Context

Runtime integration execution context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel

from app.core.enum.database import (
    IntegrationProvider,
    IntegrationSyncStatus,
    IntegrationSyncType,
)


class IntegrationContext(BaseModel):
    """
    Current integration execution.
    """

    connection_id: UUID

    org_id: UUID

    provider: IntegrationProvider

    sync_id: UUID | None = None

    sync_status: IntegrationSyncStatus | None = None

    sync_type: IntegrationSyncType | None = None

    request_id: str | None = None

    webhook_event: str | None = None