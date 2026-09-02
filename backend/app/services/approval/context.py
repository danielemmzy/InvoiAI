"""
============================================================
Approval Engine Context

Input data supplied to the approval engine.

Responsibilities
----------------
- Provide all document facts required by approval rules
- Keep rules independent from repositories
- Keep approval decisions deterministic
- Prevent rules from performing persistence

NO DATABASE
NO REPOSITORIES
NO SUPABASE
NO FASTAPI
NO SIDE EFFECTS
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.enum.database import (
    DocumentType,
    RecommendationType,
    RiskLevel,
)


@dataclass(frozen=True, slots=True)
class ApprovalContext:
    """
    Immutable input to the approval engine.

    The engine and its rules should make decisions only from
    information contained in this context.
    """

    # --------------------------------------------------------
    # Document identity
    # --------------------------------------------------------

    document_id: UUID
    org_id: UUID
    analysis_id: UUID

    # --------------------------------------------------------
    # Document information
    # --------------------------------------------------------

    document_type: DocumentType

    document_amount: Decimal

    vendor_name: str

    vendor_id: UUID | None

    # --------------------------------------------------------
    # Analysis information
    # --------------------------------------------------------

    risk_level: RiskLevel

    recommendation: RecommendationType

    # --------------------------------------------------------
    # Workflow information
    # --------------------------------------------------------

    initiated_by: UUID

    # --------------------------------------------------------
    # Optional supporting information
    # --------------------------------------------------------

    purchase_order_id: UUID | None = None

    metadata: dict[str, Any] | None = None

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @property
    def has_purchase_order(self) -> bool:
        """
        Whether the document is associated with a purchase order.
        """

        return self.purchase_order_id is not None

    @property
    def is_high_risk(self) -> bool:
        """
        Whether the analysis classified the document as high risk.
        """

        return self.risk_level == RiskLevel.HIGH

    @property
    def is_recommended_for_approval(self) -> bool:
        """
        Whether the analysis recommends approval.
        """

        return (
            self.recommendation
            == RecommendationType.APPROVE
        )

    @property
    def is_recommended_for_rejection(self) -> bool:
        """
        Whether the analysis recommends rejection.
        """

        return (
            self.recommendation
            == RecommendationType.REJECT
        )