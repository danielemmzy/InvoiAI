"""
QuickBooksAccountingProvider

A thin adapter, not a reimplementation. Every method here calls
straight into the existing, already-tested QuickBooks integration
code (BillSyncService and the QuickBooks*Sync classes) — this file
exists only so AP business logic can depend on AccountingProvider
instead of importing app.integrations.quickbooks.* directly.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.core.supabase import get_supabase
from app.integrations.quickbooks.client import QuickBooksClient
from app.integrations.quickbooks.sync.chart_of_accounts_sync import QuickBooksChartOfAccountsSync
from app.integrations.quickbooks.sync.payment_sync import QuickBooksPaymentSync
from app.integrations.quickbooks.sync.purchase_order_sync import QuickBooksPurchaseOrderSync
from app.integrations.quickbooks.sync.vendor_sync import QuickBooksVendorSync
from app.services.ap.bill_sync_service import BillSyncService
from app.services.ap.provider.accounting_provider import AccountingProvider, NoActiveAccountingProviderError


class QuickBooksAccountingProvider(AccountingProvider):

    name = "quickbooks"

    def __init__(self, org_id: UUID, db=None) -> None:
        self.org_id = org_id
        self.db = db or get_supabase()
        self.bill_sync = BillSyncService(self.db)

    async def _realm_id(self) -> str:
        conn = (
            self.db.table("integration_connections").select("realm_id")
            .eq("org_id", str(self.org_id)).eq("provider", IntegrationProvider.QUICKBOOKS.value)
            .eq("is_active", True).limit(1).execute().data
        )
        if not conn or not conn[0].get("realm_id"):
            raise NoActiveAccountingProviderError(f"No active QuickBooks connection for org {self.org_id}.")
        return conn[0]["realm_id"]

    # =========================================================
    # Bills
    # =========================================================

    async def create_bill(self, *, org_id: UUID, document_id: UUID) -> str:
        # BillSyncService.push_to_quickbooks already branches on whether
        # the document has an erp_bill_id and creates vs. updates
        # accordingly — both create_bill and update_bill delegate to it
        # rather than splitting logic that's already correct as one path.
        return await self.bill_sync.push_to_quickbooks(org_id=org_id, document_id=document_id)

    async def update_bill(self, *, org_id: UUID, document_id: UUID) -> str:
        return await self.bill_sync.push_to_quickbooks(org_id=org_id, document_id=document_id)

    async def get_bill(self, *, org_id: UUID, external_bill_id: str) -> dict[str, Any]:
        realm_id = await self._realm_id()
        client = QuickBooksClient(org_id=org_id, realm_id=realm_id)
        result = await client.get(f"/bill/{external_bill_id}")
        return result.get("Bill") or {}

    # =========================================================
    # Sync (ERP -> InvoiAI)
    # =========================================================

    async def sync_chart_of_accounts(self, *, org_id: UUID) -> dict[str, int]:
        realm_id = await self._realm_id()
        return await QuickBooksChartOfAccountsSync(org_id=org_id, realm_id=realm_id).sync()

    async def sync_vendor(self, *, org_id: UUID) -> dict[str, int]:
        realm_id = await self._realm_id()
        return await QuickBooksVendorSync(org_id=org_id, realm_id=realm_id).sync()

    async def sync_purchase_orders(self, *, org_id: UUID) -> dict[str, int]:
        realm_id = await self._realm_id()
        return await QuickBooksPurchaseOrderSync(org_id=org_id, realm_id=realm_id).sync()

    async def sync_payment(self, *, org_id: UUID) -> dict[str, int]:
        realm_id = await self._realm_id()
        return await QuickBooksPaymentSync(org_id=org_id, realm_id=realm_id).sync()
