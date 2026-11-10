"""
============================================================
Accounting Provider Abstraction

AP business logic (BillSyncWorker, PaymentInstructionService,
etc.) should depend on this interface, never on
app.integrations.quickbooks.* directly — that keeps the AP
pipeline provider-independent, per the spec's ERP abstraction
requirement.

QuickBooksAccountingProvider (quickbooks_provider.py) is a real
implementation that delegates to the existing, already-tested
QuickBooks integration code (BillSyncService, the QuickBooks*Sync
classes) — it does not reimplement any of that logic, only wraps
it behind this shared shape.

There is no Xero (or other) implementation yet. get_provider()
raises NotImplementedError with a clear message for any
unconfigured/unsupported provider rather than silently no-op'ing
or pretending to sync.
============================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class AccountingProviderError(Exception):
    pass


class NoActiveAccountingProviderError(AccountingProviderError):
    pass


class AmbiguousAccountingProviderError(AccountingProviderError):
    pass


class AccountingProvider(ABC):

    name: str = "abstract"

    @abstractmethod
    async def create_bill(self, *, org_id: UUID, document_id: UUID) -> str:
        """Pushes a coded, approved document to the ERP as a new bill. Returns the ERP's bill id."""
        raise NotImplementedError

    @abstractmethod
    async def update_bill(self, *, org_id: UUID, document_id: UUID) -> str:
        """Re-pushes an already-synced document (e.g. after a correction). Returns the ERP's bill id."""
        raise NotImplementedError

    @abstractmethod
    async def get_bill(self, *, org_id: UUID, external_bill_id: str) -> dict[str, Any]:
        """Fetches a bill's current state directly from the ERP (not from InvoiAI's cached copy)."""
        raise NotImplementedError

    @abstractmethod
    async def sync_chart_of_accounts(self, *, org_id: UUID) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    async def sync_vendor(self, *, org_id: UUID) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    async def sync_purchase_orders(self, *, org_id: UUID) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    async def sync_payment(self, *, org_id: UUID) -> dict[str, int]:
        raise NotImplementedError


async def get_accounting_provider(org_id: UUID, db=None) -> AccountingProvider:
    """
    Resolves the org's configured, active accounting provider.
    The single active connection is the dispatch key. Unsupported provider
    imports remain unavailable until their provider tickets are proven.
    """
    from app.core.enum.database import IntegrationProvider
    from app.core.supabase import get_supabase
    from app.services.ap.provider.quickbooks_provider import QuickBooksAccountingProvider

    database = db or get_supabase()

    connections = (
        database.table("integration_connections").select("id,provider")
        .eq("org_id", str(org_id)).eq("is_active", True).execute().data
        or []
    )
    if not connections:
        raise NoActiveAccountingProviderError(f"No active accounting provider is connected for org {org_id}.")
    if len(connections) != 1:
        raise AmbiguousAccountingProviderError(
            f"Expected one active accounting connection for org {org_id}; found {len(connections)}."
        )

    connection = connections[0]
    provider = connection.get("provider")
    if provider == IntegrationProvider.QUICKBOOKS.value:
        return QuickBooksAccountingProvider(
            org_id=org_id, db=database, connection_id=connection["id"]
        )
    raise NotImplementedError(
        f"Chart of Accounts import for {provider} is not implemented in this ticket."
    )
