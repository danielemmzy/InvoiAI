"""Central V2 authorization dependencies.

Authentication establishes the user identity. Organization context resolves the
active organization from an actual org_members membership. This module then
authorizes the request using the membership-derived role/permissions.

Callers must never authorize from organization_id, role, or plan supplied by
the request body or JWT metadata.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from fastapi import Depends, HTTPException, status

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context


def require_permission(permission: str) -> Callable[..., Awaitable[None]]:
    async def _dependency(
        user: AuthUser = Depends(get_current_user),
        ctx: OrganizationContext = Depends(get_org_context),
    ) -> None:
        if permission not in ctx.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient organization permission.",
            )
    return _dependency
