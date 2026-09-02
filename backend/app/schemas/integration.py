from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum.database import (
    DocumentType,
    IntegrationProvider,
    IntegrationSyncStatus,
    IntegrationSyncType,
)

# ============================================================
# Integration Connection Response
# ============================================================

class IntegrationConnectionResponse(BaseModel):
    """
    Integration connection returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    provider: IntegrationProvider

    token_type: str | None

    token_scope: str | None

    expires_at: datetime | None

    realm_id: str | None

    tenant_id: str | None

    account_id: str | None

    account_name: str | None

    account_email: str | None

    is_active: bool

    last_error: str | None

    last_error_at: datetime | None

    error_count: int

    health_status: str

    sync_enabled: bool

    sync_interval_mins: int

    sync_from_date: date | None

    auto_analyze: bool

    document_types_to_sync: list[DocumentType]

    metadata: dict[str, Any]

    connected_by: UUID | None

    created_at: datetime

    updated_at: datetime

# ============================================================
# Integration Sync Response
# ============================================================

class IntegrationSyncResponse(BaseModel):
    """
    Integration sync returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    connection_id: UUID

    org_id: UUID

    provider: IntegrationProvider

    status: IntegrationSyncStatus

    sync_type: IntegrationSyncType

    cursor_before: str | None

    cursor_after: str | None

    documents_found: int

    documents_created: int

    documents_updated: int

    documents_skipped: int

    documents_failed: int

    error_details: dict[str, Any]

    started_at: datetime

    completed_at: datetime | None

    duration_ms: int

# ============================================================
# Integration Webhook Response
# ============================================================

class IntegrationWebhookResponse(BaseModel):
    """
    Integration webhook returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    connection_id: UUID

    org_id: UUID

    provider: IntegrationProvider

    event_type: str

    event_id: str

    payload: dict[str, Any]

    processed: bool

    processed_at: datetime | None

    document_id: UUID | None

    error: str | None

    received_at: datetime


# ============================================================
# Lists
# ============================================================

class IntegrationConnectionListResponse(BaseModel):
    items: list[IntegrationConnectionResponse] = Field(default_factory=list)
    total: int


class IntegrationSyncListResponse(BaseModel):
    items: list[IntegrationSyncResponse] = Field(default_factory=list)
    total: int


class IntegrationWebhookListResponse(BaseModel):
    items: list[IntegrationWebhookResponse] = Field(default_factory=list)
    total: int