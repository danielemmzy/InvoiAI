"""
============================================================
Integration Domain Models

Mirror PostgreSQL tables.

- integration_connections
- integration_syncs
- integration_webhooks

Repositories return these models only.
============================================================
"""

from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.domain.base import DomainModel
from app.core.enum.database import (
    IntegrationProvider,
    IntegrationSyncStatus,
    IntegrationSyncType,
)


# ============================================================
# Integration Connection
# ============================================================

class IntegrationConnection(DomainModel):
    """
    Mirrors integration_connections.
    """

    id: UUID

    org_id: UUID

    provider: IntegrationProvider

    access_token: str

    refresh_token: str | None = None

    token_type: str | None = None

    token_scope: str | None = None

    expires_at: Any | None = None

    realm_id: str | None = None

    tenant_id: str | None = None

    account_id: str | None = None

    account_name: str | None = None

    account_email: str | None = None

    is_active: bool

    last_error: str | None = None

    last_error_at: Any | None = None

    error_count: int

    health_status: str

    sync_enabled: bool

    sync_interval_mins: int

    sync_from_date: Any | None = None

    auto_analyze: bool

    document_types_to_sync: list[str] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)

    connected_by: UUID | None = None

    created_at: Any

    updated_at: Any


# ============================================================
# Integration Sync
# ============================================================

class IntegrationSync(DomainModel):
    """
    Mirrors integration_syncs.
    """

    id: UUID

    connection_id: UUID

    org_id: UUID

    provider: IntegrationProvider

    status: IntegrationSyncStatus

    sync_type: IntegrationSyncType

    cursor_before: str | None = None

    cursor_after: str | None = None

    documents_found: int

    documents_created: int

    documents_updated: int

    documents_skipped: int

    documents_failed: int

    error_details: dict[str, Any] = Field(default_factory=dict)

    started_at: Any

    completed_at: Any | None = None


# ============================================================
# Integration Webhook
# ============================================================

class IntegrationWebhook(DomainModel):
    """
    Mirrors integration_webhooks.
    """

    id: UUID

    connection_id: UUID

    org_id: UUID

    provider: IntegrationProvider

    event_type: str

    event_id: str

    payload: dict[str, Any] = Field(default_factory=dict)

    processed: bool

    processed_at: Any | None = None

    document_id: UUID | None = None

    error: str | None = None

    received_at: Any

