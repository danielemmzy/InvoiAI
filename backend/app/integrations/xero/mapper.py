from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.core.enum.database import IntegrationProvider
from app.integrations.base.mapper import BaseIntegrationMapper

from app.models.domain.document import Document
from app.models.domain.payment import Payment
from app.models.domain.purchase_order import PurchaseOrder
from app.models.domain.vendor import Vendor


class XeroMapper(BaseIntegrationMapper):
    """
    Xero -> Domain Mapper

    Uses the same domain models as QuickBooks.
    """

    # =====================================================
    # Generic interface
    # =====================================================

    def to_domain(
        self,
        payload: dict,
    ):
        raise NotImplementedError(
            "Use provider-specific mapping methods."
        )

    def to_provider(
        self,
        model,
    ) -> dict:

        raise NotImplementedError()

    # =====================================================
    # Contacts
    # =====================================================

    def vendor(
        self,
        *,
        org_id,
        data: dict,
    ) -> Vendor:

        return Vendor(
            id=uuid4(),
            org_id=org_id,
            external_id=self.require(
                data,
                "ContactID",
            ),
            provider=IntegrationProvider.XERO,
            name=self.optional(
                data,
                "Name",
            ),
            email=self.optional(
                data,
                "EmailAddress",
            ),
            phone=(
                data.get("Phones", [{}])[0]
                .get("PhoneNumber")
            ),
            tax_id=self.optional(
                data,
                "TaxNumber",
            ),
            website=self.optional(
                data,
                "Website",
            ),
            is_active=not self.optional(
                data,
                "IsArchived",
                False,
            ),
        )

    customer = vendor

    # =====================================================
    # Bills
    # =====================================================

    def bill(
        self,
        *,
        org_id,
        vendor_id,
        data: dict,
    ) -> Document:

        return Document(
            id=uuid4(),
            org_id=org_id,
            vendor_id=vendor_id,
            external_id=self.require(
                data,
                "InvoiceID",
            ),
            provider=IntegrationProvider.XERO,
            document_number=self.optional(
                data,
                "InvoiceNumber",
            ),
            total_amount=Decimal(
                str(
                    self.optional(
                        data,
                        "Total",
                        0,
                    )
                )
            ),
            currency=self.optional(
                data,
                "CurrencyCode",
                "USD",
            ),
            status=self.optional(
                data,
                "Status",
            ),
        )

    invoice = bill

    # =====================================================
    # Purchase Orders
    # =====================================================

    def purchase_order(
        self,
        *,
        org_id,
        vendor_id,
        data: dict,
    ) -> PurchaseOrder:

        return PurchaseOrder(
            id=uuid4(),
            org_id=org_id,
            vendor_id=vendor_id,
            po_number=self.optional(
                data,
                "PurchaseOrderNumber",
            ),
            description=self.optional(
                data,
                "Reference",
            ),
            amount=Decimal(
                str(
                    self.optional(
                        data,
                        "Total",
                        0,
                    )
                )
            ),
            currency=self.optional(
                data,
                "CurrencyCode",
                "USD",
            ),
            issued_date=self.optional(
                data,
                "Date",
            ),
            provider=IntegrationProvider.XERO,
            external_id=self.require(
                data,
                "PurchaseOrderID",
            ),
            status=self.optional(
                data,
                "Status",
            ),
            metadata=data,
        )

    # =====================================================
    # Payments
    # =====================================================

    def payment(
        self,
        *,
        org_id,
        vendor_id,
        document_id,
        data: dict,
    ) -> Payment:

        return Payment(
            id=uuid4(),
            org_id=org_id,
            vendor_id=vendor_id,
            document_id=document_id,
            payment_number=self.optional(
                data,
                "PaymentID",
            ),
            external_id=self.require(
                data,
                "PaymentID",
            ),
            provider=IntegrationProvider.XERO,
            payment_method=(
                data.get("Account", {})
                .get("Name")
            ),
            amount=float(
                self.optional(
                    data,
                    "Amount",
                    0,
                )
            ),
            currency=self.optional(
                data,
                "CurrencyCode",
                "USD",
            ),
            payment_date=self.optional(
                data,
                "Date",
            ),
            status="completed",
            reference=self.optional(
                data,
                "Reference",
            ),
            metadata=data,
        )