from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

WorkspaceType = Literal["personal", "business"]

# Standard SaaS company-size bands — the same shape Stripe, HubSpot, and
# most B2B onboarding flows use. Kept as a small closed set rather than a
# free-text field so it stays usable for segmentation later (sales
# routing, plan-fit nudges, aggregate reporting) instead of turning into
# unstructured text nobody can group on.
CompanySize = Literal["1", "2-10", "11-50", "51-200", "201-500", "500+"]


class WorkspaceCreate(BaseModel):
    type: WorkspaceType
    name: str | None = Field(default=None, max_length=120)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    country: str | None = Field(default=None, max_length=2)
    # Only meaningful for type="business" — ignored for personal
    # workspaces. Optional so existing API consumers (mobile client,
    # scripts) don't break; the frontend makes it required in the UI
    # for business signups.
    company_size: CompanySize | None = None


class WorkspaceSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    type: WorkspaceType
    role: str
    plan: str
    currency: str
    created_at: datetime
