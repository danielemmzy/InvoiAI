from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.core.enum.database import IntegrationProvider


@dataclass(slots=True)
class PurchaseOrder:
    """
    Purchase Order domain model.

    Represents a purchase order inside InvoiAI.

    Provider-agnostic.

    Used by:

    • QuickBooks
    • Xero
    • Sage
    • ERP integrations
    """

    id: UUID

    org_id: UUID

    vendor_id: UUID | None = None

    po_number: str = ""

    description: str | None = None

    amount: Decimal = Decimal("0.00")

    currency: str = "USD"

    issued_date: date | None = None

    expiry_date: date | None = None

    is_open: bool = True

    matched_amount: Decimal = Decimal("0.00")

    created_by: UUID | None = None

    # ------------------------------------------
    # Integration
    # ------------------------------------------

    provider: IntegrationProvider | None = None

    external_id: str | None = None

    status: str | None = None

    synced_at: datetime | None = None

    last_modified_external: datetime | None = None

    # ------------------------------------------
    # Metadata
    # ------------------------------------------

    metadata: dict = field(default_factory=dict)

    # ------------------------------------------
    # Audit
    # ------------------------------------------

    created_at: datetime | None = None

    updated_at: datetime | None = None