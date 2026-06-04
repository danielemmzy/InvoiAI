from fastapi import APIRouter, Request
from app.core.limiter import limiter
from app.models.invoice import SUPPORTED_INDUSTRIES, INDUSTRY_LABELS, IndustriesResponse

router = APIRouter(prefix="/industries", tags=["Industries"])


@router.get("", response_model=IndustriesResponse)
@limiter.limit("60/minute")
async def get_industries(request: Request):
    """
    Returns all supported industries for the upload dropdown.
    Frontend calls this once on load.
    Adding a new industry = one line in models/invoice.py.
    """
    return IndustriesResponse(
        industries=[
            {"value": key, "label": INDUSTRY_LABELS[key]}
            for key in SUPPORTED_INDUSTRIES
        ]
    )