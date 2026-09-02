from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.context import AuthUser
from app.core.auth import get_current_user
from app.core.container import get_container
from app.core.limiter import limiter
from app.schemas.workspace import WorkspaceCreate, WorkspaceSummary

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=list[WorkspaceSummary])
@limiter.limit("30/minute")
async def list_workspaces(request: Request, response: Response, user: AuthUser = Depends(get_current_user)):
    return await get_container().organization_service.list_user_workspaces(user.id)


@router.post("", response_model=WorkspaceSummary, status_code=201)
@limiter.limit("10/minute")
async def create_workspace(
    request: Request,
    response: Response,
    body: WorkspaceCreate,
    user: AuthUser = Depends(get_current_user),
):
    return await get_container().organization_service.create_workspace(
        user=user,
        workspace_type=body.type,
        name=body.name,
        currency=body.currency.upper(),
        country=body.country.upper() if body.country else None,
        company_size=body.company_size,
    )
