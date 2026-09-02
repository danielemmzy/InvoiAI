from __future__ import annotations

from app.integrations.xero.sync.vendor_sync import (
    XeroVendorSync,
)
from app.integrations.xero.sync.customer_sync import (
    XeroCustomerSync,
)
from app.integrations.xero.sync.bill_sync import (
    XeroBillSync,
)
from app.integrations.xero.sync.invoice_sync import (
    XeroInvoiceSync,
)
from app.integrations.xero.sync.purchase_order_sync import (
    XeroPurchaseOrderSync,
)
from app.integrations.xero.sync.payment_sync import (
    XeroPaymentSync,
)


class XeroSyncService:
    """
    Xero synchronization orchestrator.

    Responsibilities
    ----------------
    • Execute synchronization in ERP dependency order
    • Delegate all synchronization work to resource sync services

    No mapping.

    No persistence.

    No API logic.
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.vendor_sync = XeroVendorSync(
            org_id=org_id,
        )

        self.customer_sync = XeroCustomerSync(
            org_id=org_id,
        )

        self.bill_sync = XeroBillSync(
            org_id=org_id,
        )

        self.invoice_sync = XeroInvoiceSync(
            org_id=org_id,
        )

        self.purchase_order_sync = (
            XeroPurchaseOrderSync(
                org_id=org_id,
            )
        )

        self.payment_sync = XeroPaymentSync(
            org_id=org_id,
        )

    # =====================================================
    # Full Synchronization
    # =====================================================

    async def sync(self) -> dict:

        return {
            "vendors": await self.vendor_sync.sync(),
            "customers": await self.customer_sync.sync(),
            "bills": await self.bill_sync.sync(),
            "invoices": await self.invoice_sync.sync(),
            "purchase_orders": await self.purchase_order_sync.sync(),
            "payments": await self.payment_sync.sync(),
        }