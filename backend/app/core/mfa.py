from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.enum.database import OrgRole
from app.core.ocm import get_org_context
from app.services.auth import mfa_service
from app.services.auth.mfa_security import is_recent_aal2


async def require_fresh_mfa(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
) -> None:
    if ctx.role not in {OrgRole.OWNER, OrgRole.ADMIN}:
        return
    if is_recent_aal2(user.aal, user.mfa_verified_at):
        return
    if mfa_service.has_recovery_step_up(user.id, user.session_id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "MFA_STEP_UP_REQUIRED",
            "message": "Verify your authenticator in Security, then retry this action.",
        },
    )


def require_recent_supabase_mfa(user: AuthUser) -> None:
    if not is_recent_aal2(user.aal, user.mfa_verified_at):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MFA_STEP_UP_REQUIRED",
                "message": "Verify your authenticator before changing MFA factors.",
            },
        )
