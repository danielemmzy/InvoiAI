from __future__ import annotations

from app.integrations.base.client import BaseAPIClient
from app.core.enum.database import IntegrationProvider
from app.repositories.integration.integration_repository import IntegrationConnectionRepository
from app.services.token_service import TokenService


class QuickBooksClient(BaseAPIClient):
    """
    QuickBooks API client.

    Responsibilities
    ----------------
    • Execute authenticated requests
    • Provide QuickBooks endpoints
    • No business logic
    """

    def __init__(
        self,
        *,
        org_id,
        realm_id: str,
    ):

        super().__init__()

        self.org_id = org_id
        self.realm_id = realm_id

        self.tokens = TokenService(
            repository=IntegrationConnectionRepository(),
        )

    @property
    def base_url(self) -> str:

        return (
            "https://quickbooks.api.intuit.com"
            f"/v3/company/{self.realm_id}"
        )

    async def access_token(self) -> str:
        return await self.tokens.get_access_token(
            org_id=self.org_id,
            provider=IntegrationProvider.QUICKBOOKS,
        )

    # ====================================================
    # Chart of Accounts
    # ====================================================

    async def accounts(self, *, start_position: int = 1, max_results: int = 1000):
        """Fetch one page of the QuickBooks Chart of Accounts.

        QuickBooks Query API is paginated. Keeping pagination in the provider
        client prevents provider-specific transport concerns from leaking into
        the accounting domain layer.
        """
        return await self.get(
            "/query",
            params={
                "query": (
                    "SELECT * FROM Account "
                    f"STARTPOSITION {start_position} MAXRESULTS {max_results}"
                ),
            },
        )

    # ====================================================
    # Vendors
    # ====================================================

    async def vendors(self):

        return await self.get(
            "/query",
            params={
                "query": "SELECT * FROM Vendor",
            },
        )

    # ====================================================
    # Customers
    # ====================================================

    async def customers(self):

        return await self.get(
            "/query",
            params={
                "query": "SELECT * FROM Customer",
            },
        )

    # ====================================================
    # Invoices
    # ====================================================

    async def invoices(self):

        return await self.get(
            "/query",
            params={
                "query": "SELECT * FROM Invoice",
            },
        )

    # ====================================================
    # Bills
    # ====================================================

    async def bills(self):

        return await self.get(
            "/query",
            params={
                "query": "SELECT * FROM Bill",
            },
        )

    # ====================================================
    # Purchase Orders
    # ====================================================

    async def purchase_orders(self):

        return await self.get(
            "/query",
            params={
                "query": "SELECT * FROM PurchaseOrder",
            },
        )

    # ====================================================
    # Payments
    # ====================================================

    async def payments(self):

        return await self.get(
            "/query",
            params={
                "query": "SELECT * FROM Payment",
            },
        )
    async def create_bill(self, payload: dict) -> dict:
        return await self.post("/bill", json=payload)

    async def update_bill(self, bill_id: str, payload: dict) -> dict:
        # QuickBooks requires SyncToken for updates. Fetch the current bill first.
        current = await self.get(f"/bill/{bill_id}")
        bill = current.get("Bill") or {}
        payload = {**payload, "Id": bill_id, "SyncToken": bill.get("SyncToken", "0")}
        return await self.post("/bill?operation=update", json=payload)
