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
    Today this can only ever return a QuickBooksAccountingProvider
    or raise — there is nothing else configured for any org yet.
    """
    from app.core.enum.database import IntegrationProvider
    from app.core.supabase import get_supabase
    from app.services.ap.provider.quickbooks_provider import QuickBooksAccountingProvider

    database = db or get_supabase()

    qb_connection = (
        database.table("integration_connections").select("id")
        .eq("org_id", str(org_id)).eq("provider", IntegrationProvider.QUICKBOOKS.value)
        .eq("is_active", True).limit(1).execute().data
    )
    if qb_connection:
        return QuickBooksAccountingProvider(org_id=org_id, db=database)

    xero_connection = (
        database.table("integration_connections").select("id")
        .eq("org_id", str(org_id)).eq("provider", "xero")
        .eq("is_active", True).limit(1).execute().data
    )
    if xero_connection:
        raise NotImplementedError(
            "A Xero connection exists for this organization, but Xero sync is not implemented yet — "
            "only the AccountingProvider interface shape is in place. Reconnect QuickBooks, or implement "
            "app/services/ap/provider/xero_provider.py."
        )

    raise NoActiveAccountingProviderError(f"No active accounting provider is connected for org {org_id}.")
