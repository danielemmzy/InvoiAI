from fastapi import APIRouter, Request, Response
from app.core.industries import SUPPORTED_INDUSTRIES, INDUSTRY_LABELS
from app.core.cache import cache
from app.core.cache_keys import industries as industries_cache_key
from app.core.limiter import limiter

router = APIRouter(prefix="/industries", tags=["Industries"])


@router.get("")
@limiter.limit("60/minute")
async def list_industries(request: Request, response: Response):
    key = industries_cache_key("v2")
    cached = await cache.get(key)
    if cached is not None:
        return cached
    result = {
        "industries": [
            {"value": k, "label": INDUSTRY_LABELS[k]} for k in SUPPORTED_INDUSTRIES
        ]
    }
    await cache.set(key=key, value=result, ttl=86400)
    return result
