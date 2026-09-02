"""
============================================================
Vendor Context

Runtime vendor context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel

from app.core.enum.database import RiskLevel


class VendorContext(BaseModel):
    """
    Current vendor.
    """

    vendor_id: UUID

    org_id: UUID

    name: str

    normalized_name: str

    risk_score: int = 0

    risk_level: RiskLevel | None = None

    is_verified: bool = False

    is_preferred: bool = False

    is_blocked: bool = False