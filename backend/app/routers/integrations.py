from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status, Request, Response
from fastapi.responses import RedirectResponse
import httpx

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.container import get_container
from app.core.ocm import get_org_context
from app.core.permissions import MANAGE_INTEGRATIONS, VIEW_INTEGRATIONS
from app.core.config import settings
from app.core.limiter import limiter
from app.core.enum.database import IntegrationProvider
from app.schemas.integration import IntegrationConnectionResponse

router = APIRouter(prefix="/integrations", tags=["Integrations"])


async def _require_permission(
    *,
    user: AuthUser,
    ctx: OrganizationContext,
    permission: str,
) -> None:
    allowed = await get_container().organization_service.has_permission(
        org_id=ctx.org_id,
        user_id=user.id,
        permission=permission,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient organization permission.",
        )


@router.post("/quickbooks/connect")
@limiter.limit("10/minute")
async def connect_quickbooks(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    await _require_permission(
        user=user,
        ctx=ctx,
        permission=MANAGE_INTEGRATIONS,
    )
    url = get_container().integration_service.build_authorization_url(
        provider=IntegrationProvider.QUICKBOOKS,
        user_id=user.id,
        org_id=ctx.org_id,
    )
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/quickbooks/callback")
@limiter.limit("20/minute")
async def quickbooks_callback(
    response: Response,
    request: Request,
    background_tasks: BackgroundTasks,
    code: str = Query(...),
    state: str = Query(...),
    realm_id: str | None = Query(default=None, alias="realmId"),
):
    service = get_container().integration_service
    try:
        connection = await service.complete_oauth(
            provider=IntegrationProvider.QUICKBOOKS,
            code=code,
            state=state,
            realm_id=realm_id,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="OAuth provider request failed") from exc

    # The scheduler remains the durable recurring-sync mechanism. The
    # background task provides the expected first-sync UX immediately after
    # OAuth without making the OAuth callback wait for a full ERP sync.
    if background_tasks is not None:
        background_tasks.add_task(
            get_container().quickbooks_worker.run,
            org_id=connection.org_id,
            realm_id=connection.realm_id or "",
        )

    return RedirectResponse(
        url=f"{settings.frontend_app_url.rstrip('/')}/integrations?provider=quickbooks&status=connected",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/xero/connect")
@limiter.limit("10/minute")
async def connect_xero(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    await _require_permission(
        user=user,
        ctx=ctx,
        permission=MANAGE_INTEGRATIONS,
    )
    url = get_container().integration_service.build_authorization_url(
        provider=IntegrationProvider.XERO,
        user_id=user.id,
        org_id=ctx.org_id,
    )
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/xero/callback")
@limiter.limit("20/minute")
async def xero_callback(
    response: Response,
    request: Request,
    background_tasks: BackgroundTasks,
    code: str = Query(...),
    state: str = Query(...),
):
    service = get_container().integration_service
    try:
        connection = await service.complete_oauth(
            provider=IntegrationProvider.XERO,
            code=code,
            state=state,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="OAuth provider request failed") from exc

    if background_tasks is not None:
        background_tasks.add_task(
            get_container().xero_worker.run,
            org_id=connection.org_id,
        )

    return RedirectResponse(
        url=f"{settings.frontend_app_url.rstrip('/')}/integrations?provider=xero&status=connected",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("", response_model=list[IntegrationConnectionResponse])
async def list_integrations(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    await _require_permission(
        user=user,
        ctx=ctx,
        permission=VIEW_INTEGRATIONS,
    )
    connections = await get_container().integration_service.list_connections(
        org_id=ctx.org_id,
    )
    return [
        IntegrationConnectionResponse.model_validate(
            connection,
            from_attributes=True,
        )
        for connection in connections
    ]


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_integration(
    connection_id: str,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    await _require_permission(
        user=user,
        ctx=ctx,
        permission=MANAGE_INTEGRATIONS,
    )
    from uuid import UUID

    try:
        connection_uuid = UUID(connection_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid connection id") from exc

    repository = get_container().integration_repository
    connection = await repository.get_connection(connection_uuid)
    if connection is None or connection.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="Integration connection not found")

    await get_container().integration_service.disconnect(connection=connection)
