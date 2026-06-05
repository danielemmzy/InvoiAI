from fastapi import APIRouter, Request
from app.core.limiter import limiter
from app.models.invoice import SUPPORTED_INDUSTRIES, INDUSTRY_LABELS, IndustriesResponse

router = APIRouter(prefix="/industries", tags=["Industries"])


@router.get("", response_model=IndustriesResponse)
@limiter.limit("60/minute")
async def get_industries(request: Request):
    """
    Public endpoint — no auth required.
    Returns the industry list for the upload dropdown.
    Frontend calls this once on load.
    """
    return IndustriesResponse(
        industries=[
            {"value": k, "label": INDUSTRY_LABELS[k]}
            for k in SUPPORTED_INDUSTRIES
        ]
    )