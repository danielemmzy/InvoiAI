from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context
from app.core.container import get_container
from app.core.limiter import limiter
from app.core.authorization import require_permission
from app.core.permissions import VIEW_DOCUMENTS

router = APIRouter(prefix="/export", tags=["Export"])


async def _export(request, document_id, user, ctx, fmt):
    doc = await get_container().document_service.get_document(document_id)
    if doc.org_id != ctx.org_id:
        raise HTTPException(404, "Document not found")
    result = await get_container().export_service.export(
        document_id=document_id, exported_by=user.id, export_format=fmt
    )
    if result.file_bytes is not None:
        return Response(
            content=result.file_bytes,
            media_type=result.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"'
            },
        )
    return {"url": result.url}


@router.get("/{document_id}/excel")
@limiter.limit("10/minute")
async def excel(
    response: Response,
    request: Request,
    document_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
):
    return await _export(request, document_id, user, ctx, "excel")


@router.get("/{document_id}/csv")
@limiter.limit("10/minute")
async def csv(
    response: Response,
    request: Request,
    document_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
):
    return await _export(request, document_id, user, ctx, "csv")


@router.post("/{document_id}/sheets")
@limiter.limit("10/minute")
async def sheets(
    response: Response,
    request: Request,
    document_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_DOCUMENTS)),
):
    return await _export(request, document_id, user, ctx, "google_sheets")
