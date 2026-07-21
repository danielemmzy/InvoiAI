# ============================================================
# app/models/integration.py
#
# External integrations
#
# Supports:
# - QuickBooks
# - Xero
# - Google Drive
# - Gmail
# - Outlook
# - Future ERP systems
# ============================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.app.core.enum.enums import (
    IntegrationProvider,
    IntegrationStatus,
)


# ============================================================
# Integration Connection
# ============================================================

class IntegrationConnectionCreate(BaseModel):
    """
    OAuth callback creates one of these.
    """

    provider: IntegrationProvider

    external_tenant_id: Optional[str] = None

    external_account_name: Optional[str] = None


class IntegrationConnectionUpdate(BaseModel):

    status: Optional[IntegrationStatus] = None

    external_account_name: Optional[str] = None


class IntegrationConnection(BaseModel):

    id: str

    org_id: str

    provider: IntegrationProvider

    status: IntegrationStatus

    external_tenant_id: Optional[str]

    external_account_name: Optional[str]

    connected_by: str

    connected_at: Optional[datetime]

    expires_at: Optional[datetime]

    last_sync_at: Optional[datetime]

    created_at: Optional[datetime]

    updated_at: Optional[datetime]


# ============================================================
# Synchronization
# ============================================================

class IntegrationSync(BaseModel):

    id: str

    connection_id: str

    job_id: Optional[str]

    started_at: Optional[datetime]

    finished_at: Optional[datetime]

    success: bool

    imported_documents: int

    imported_vendors: int

    imported_transactions: int

    error: Optional[str]


# ============================================================
# Webhooks
# ============================================================

class IntegrationWebhook(BaseModel):

    id: str

    connection_id: str

    event_type: str

    external_event_id: Optional[str]

    processed: bool

    received_at: datetime

    processed_at: Optional[datetime]


# ============================================================
# Connection Summary
# ============================================================

class IntegrationSummary(BaseModel):

    id: str

    provider: IntegrationProvider

    status: IntegrationStatus

    external_account_name: Optional[str]

    last_sync_at: Optional[datetime]


# ============================================================
# Integration Page
# ============================================================

class IntegrationPage(BaseModel):

    integrations: list[IntegrationSummary]

    count: int

    offset: int

    limit: int