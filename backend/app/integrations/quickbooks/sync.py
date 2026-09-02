from __future__ import annotations


from app.integrations.quickbooks.sync.customer_sync import (
    QuickBooksCustomerSync,
)
from app.integrations.quickbooks.sync.bill_sync import (
    QuickBooksBillSync,
)
from app.integrations.quickbooks.sync.invoice_sync import (
    QuickBooksInvoiceSync,
)
from app.integrations.quickbooks.sync.purchase_order_sync import (
    QuickBooksPurchaseOrderSync,
)
from app.integrations.quickbooks.sync.payment_sync import (
    QuickBooksPaymentSync,
)
from app.integrations.quickbooks.sync.vendor_sync import QuickBooksVendorSync
from app.integrations.quickbooks.sync.chart_of_accounts_sync import QuickBooksChartOfAccountsSync


class QuickBooksSyncService:
    """
    QuickBooks synchronization orchestrator.

    Responsibilities
    ----------------
    • Execute provider sync pipeline
    • No mapping
    • No persistence
    • No business logic
    """

    def __init__(
        self,
        *,
        org_id,
        realm_id: str,
    ) -> None:

        self.vendor_sync = QuickBooksVendorSync(
            org_id=org_id,
            realm_id=realm_id,
        )

        self.customer_sync = QuickBooksCustomerSync(
            org_id=org_id,
            realm_id=realm_id,
        )

        self.bill_sync = QuickBooksBillSync(
            org_id=org_id,
            realm_id=realm_id,
        )

        self.invoice_sync = QuickBooksInvoiceSync(
            org_id=org_id,
            realm_id=realm_id,
        )

        self.purchase_order_sync = (
            QuickBooksPurchaseOrderSync(
                org_id=org_id,
                realm_id=realm_id,
            )
        )

        self.payment_sync = QuickBooksPaymentSync(
            org_id=org_id,
            realm_id=realm_id,
        )

        self.chart_of_accounts_sync = QuickBooksChartOfAccountsSync(
            org_id=org_id,
            realm_id=realm_id,
        )

    async def sync(self) -> dict:

        return {
            "vendors": await self.vendor_sync.sync(),
            "customers": await self.customer_sync.sync(),
            "bills": await self.bill_sync.sync(),
            "invoices": await self.invoice_sync.sync(),
            "purchase_orders": await self.purchase_order_sync.sync(),
            "payments": await self.payment_sync.sync(),
        }