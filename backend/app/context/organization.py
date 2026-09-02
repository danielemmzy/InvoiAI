"""
============================================================
Organization Context

Request-scoped organization information.

Contains the active organization together with
subscription and feature information needed during
request execution.

Never persisted.
============================================================
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enum.database import PlanType, OrgRole


class OrganizationContext(BaseModel):
    """
    Active organization context.
    """

    org_id: UUID

    name: str

    slug: str

    plan: PlanType

    # Authoritative organization membership role/permissions resolved by OCM.
    role: OrgRole
    permissions: set[str] = Field(default_factory=set)

    document_limit: int

    documents_used: int = 0

    remaining_documents: int = 0

    ai_enabled: bool = True

    copilot_enabled: bool = True

    analytics_enabled: bool = True

    embeddings_enabled: bool = True

    default_currency: str

    timezone: str

    feature_flags: dict[str, bool] = Field(default_factory=dict)

    metadata: dict[str, str] = Field(default_factory=dict)

    storage_bytes: int = 0

    ai_tokens_used: int = 0

    ai_cost_usd: Decimal = Decimal("0")