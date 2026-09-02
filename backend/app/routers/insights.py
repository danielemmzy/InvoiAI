"""
============================================================
Insights Router

Flow 10 — GET /api/v1/insights, PATCH /{id}/dismiss.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.context import OrganizationContext
from app.core.ocm import get_org_context
from app.mappers.insight_mapper import InsightMapper
from app.schemas.insight import InsightResponse
from app.services.insights.insight_service import InsightService
from app.core.container import get_container
from app.core.cache import cache
from app.core.cache_keys import insights as insights_cache_key
from app.core.limiter import limiter
from app.core.authorization import require_permission
from app.core.permissions import VIEW_INSIGHTS, MANAGE_INSIGHTS

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("", response_model=list[InsightResponse])
@limiter.limit("60/minute")
async def list_insights(
    response: Response,
    request: Request,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_INSIGHTS)),
    limit: int = 50,
    offset: int = 0,
):
    key = insights_cache_key(str(ctx.org_id), limit, offset)
    cached = await cache.get(key)
    if cached is not None:
        return [InsightResponse.model_validate(item) for item in cached]

    insights = await get_container().insight_service.list_active(ctx.org_id, limit, offset)
    result = InsightMapper.to_response_list(insights)
    await cache.set(
        key=key,
        value=[item.model_dump(mode="json") for item in result],
        ttl=60,
    )
    return result


@router.patch("/{insight_id}/dismiss", response_model=InsightResponse)
async def dismiss_insight(
    insight_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_INSIGHTS)),
):
    insight = await get_container().insight_service.dismiss(insight_id, ctx.org_id)
    await cache.delete_prefix(f"v2:insights:{ctx.org_id}:")
    return InsightMapper.to_response(insight)


@router.post("/generate", response_model=list[InsightResponse])
async def generate_insights_now(
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_INSIGHTS)),
):
    """
    Manual trigger for testing/demoing without waiting for the
    scheduler's daily tick — useful during development.
    """
    created = await get_container().insight_service.generate(ctx.org_id)
    await cache.delete_prefix(f"v2:insights:{ctx.org_id}:")
    return InsightMapper.to_response_list(created)
