from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.models.domain.vendor import Vendor
from app.models.domain.document import Document
from app.core.enum.database import IntegrationProvider
from app.models.domain.payment import Payment
from app.models.domain.purchase_order import PurchaseOrder


class QuickBooksMapper:
    """
    Maps QuickBooks objects into InvoiAI domain models.

    Responsibilities
    ----------------
    • QuickBooks JSON -> Vendor
    • QuickBooks JSON -> Document

    No database.

    No HTTP.

    No business logic.
    """

    # =====================================================
    # Vendor
    # =====================================================

    @staticmethod
    def vendor(
        *,
        org_id,
        data: dict,
    ) -> Vendor:

        return Vendor(
            id=uuid4(),
            org_id=org_id,
            external_id=str(data["Id"]),
            provider="quickbooks",
            name=data.get("DisplayName"),
            email=(
                data.get("PrimaryEmailAddr", {})
                .get("Address")
            ),
            phone=(
                data.get("PrimaryPhone", {})
                .get("FreeFormNumber")
            ),
            tax_id=data.get("TaxIdentifier"),
            website=data.get("WebAddr", {}).get("URI"),
            is_active=data.get("Active", True),
        )

    # =====================================================
    # Customer
    # =====================================================

    @staticmethod
    def customer(
        *,
        org_id,
        data: dict,
    ) -> Vendor:

        return Vendor(
            id=uuid4(),
            org_id=org_id,
            external_id=str(data["Id"]),
            provider="quickbooks",
            name=data.get("DisplayName"),
            email=(
                data.get("PrimaryEmailAddr", {})
                .get("Address")
            ),
            phone=(
                data.get("PrimaryPhone", {})
                .get("FreeFormNumber")
            ),
            website=data.get("WebAddr", {}).get("URI"),
            is_active=data.get("Active", True),
        )

    # =====================================================
    # Bill
    # =====================================================

    @staticmethod
    def bill(
        *,
        org_id,
        vendor_id,
        data: dict,
    ) -> Document:

        return Document(
            id=uuid4(),
            org_id=org_id,
            vendor_id=vendor_id,
            external_id=str(data["Id"]),
            provider="quickbooks",
            document_number=data.get("DocNumber"),
            total_amount=Decimal(
                str(
                    data.get(
                        "TotalAmt",
                        0,
                    )
                )
            ),
            currency=data.get(
                "CurrencyRef",
                {},
            ).get(
                "value",
                "USD",
            ),
            status="approved",
        )

    # =====================================================
    # Invoice
    # =====================================================

    @staticmethod
    def invoice(
        *,
        org_id,
        vendor_id,
        data: dict,
    ) -> Document:

        return Document(
            id=uuid4(),
            org_id=org_id,
            vendor_id=vendor_id,
            external_id=str(data["Id"]),
            provider="quickbooks",
            document_number=data.get("DocNumber"),
            total_amount=Decimal(
                str(
                    data.get(
                        "TotalAmt",
                        0,
                    )
                )
            ),
            currency=data.get(
                "CurrencyRef",
                {},
            ).get(
                "value",
                "USD",
            ),
            status="approved",
        )

    # =====================================================
    # Purchase Order
    # =====================================================

    @staticmethod
    def purchase_order(
        *,
        org_id,
        vendor_id,
        data: dict,
    ) -> PurchaseOrder:

        return PurchaseOrder(
            id=uuid4(),
            org_id=org_id,
            vendor_id=vendor_id,
            po_number=data.get("DocNumber", ""),
            description=data.get("PrivateNote"),
            amount=Decimal(str(data.get("TotalAmt", 0))),
            currency=data.get("CurrencyRef", {}).get("value", "USD"),
            issued_date=data.get("TxnDate"),
            provider=IntegrationProvider.QUICKBOOKS,
            external_id=str(data["Id"]),
            status=data.get("POStatus"),
            metadata=data,
        )


    # =====================================================
    # Payment
    # =====================================================

    @staticmethod
    def payment(
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
            payment_number=data.get("PaymentRefNum"),
            external_id=str(data["Id"]),
            provider=IntegrationProvider.QUICKBOOKS,
            payment_method=data.get("PaymentMethodRef", {}).get("name"),
            amount=float(data.get("TotalAmt", 0)),
            currency=data.get("CurrencyRef", {}).get("value", "USD"),
            payment_date=data.get("TxnDate"),
            status="completed",
            reference=data.get("PrivateNote"),
            metadata=data,
        )

    