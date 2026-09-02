from __future__ import annotations

from app.integrations.base.client import BaseAPIClient
from app.core.enum.database import IntegrationProvider
from app.repositories.integration.integration_repository import IntegrationConnectionRepository
from app.services.token_service import TokenService


class XeroClient(BaseAPIClient):
    """
    Xero API client.

    Responsibilities
    ----------------
    • Execute authenticated requests
    • Expose Xero endpoints
    • No business logic
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        super().__init__()

        self.org_id = org_id

        self.tokens = TokenService(
            repository=IntegrationConnectionRepository(),
        )

    @property
    def base_url(self) -> str:

        return "https://api.xero.com/api.xro/2.0"

    async def access_token(self) -> str:
        return await self.tokens.get_access_token(
            org_id=self.org_id,
            provider=IntegrationProvider.XERO,
        )

    async def headers(self) -> dict[str, str]:

        headers = await super().headers()

        connection = await self.tokens.get_org_connection(
            org_id=self.org_id,
            provider=IntegrationProvider.XERO,
        )
        if connection is None or not connection.tenant_id:
            raise ValueError("Xero integration has no tenant id.")

        headers["Xero-tenant-id"] = connection.tenant_id

        return headers

    # =====================================================
    # Contacts
    # =====================================================

    async def contacts(self):

        return await self.get(
            "/Contacts",
        )

    # =====================================================
    # Invoices
    # =====================================================

    async def invoices(self):

        return await self.get(
            "/Invoices",
        )

    # =====================================================
    # Bills
    # =====================================================

    async def bills(self):

        return await self.get(
            "/Invoices",
            params={
                "where": 'Type=="ACCPAY"',
            },
        )

    # =====================================================
    # Purchase Orders
    # =====================================================

    async def purchase_orders(self):

        return await self.get(
            "/PurchaseOrders",
        )

    # =====================================================
    # Payments
    # =====================================================

    async def payments(self):

        return await self.get(
            "/Payments",
        )