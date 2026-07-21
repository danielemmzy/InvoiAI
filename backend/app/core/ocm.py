"""
============================================================
app/core/ocm.py

Organization Context Middleware (OCM)

OCM is responsible for building an OrganizationContext
for every authenticated request.

It does NOT:

- query Supabase directly
- contain SQL
- perform RBAC
- perform feature checks

Those belong to:

repositories/
services/
permissions.py

============================================================
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header

from app.core.auth import get_current_user
from app.models.context import (
    AuthUser,
    OrganizationContext,
)
from app.services.organization_service import OrganizationService


async def get_org_context(
    user: AuthUser = Depends(get_current_user),
    x_org_id: Optional[str] = Header(
        default=None,
        alias="X-Org-Id",
    ),
) -> OrganizationContext:
    """
    FastAPI dependency.

    Builds the OrganizationContext for the request.

    Usage:

        @router.get(...)
        async def endpoint(
            ctx: OrganizationContext = Depends(get_org_context)
        ):
            ...

    """

    service = OrganizationService()

    return await service.build_context(
        user=user,
        org_id=x_org_id,
    )