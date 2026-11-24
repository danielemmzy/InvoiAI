from fastapi import APIRouter, Depends, Request, Response

from app.context import AuthUser
from app.core.auth import get_current_user
from app.core.container import get_container
from app.core.limiter import limiter
from app.repositories.organization.onboarding_draft_repository import OnboardingDraftRepository
from app.schemas.onboarding import (
    OnboardingComplete,
    OnboardingCompleteResponse,
    OnboardingDraftResponse,
    OnboardingDraftUpdate,
)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/draft", response_model=OnboardingDraftResponse)
@limiter.limit("60/minute")
async def get_draft(request: Request, response: Response, user: AuthUser = Depends(get_current_user)):
    row = await OnboardingDraftRepository().get(user.id)
    if row is None:
        return OnboardingDraftResponse()
    return OnboardingDraftResponse(**row)


@router.put("/draft", response_model=OnboardingDraftResponse)
@limiter.limit("60/minute")
async def save_draft(request: Request, response: Response, body: OnboardingDraftUpdate, user: AuthUser = Depends(get_current_user)):
    row = await OnboardingDraftRepository().save(user.id, step=body.step, data=body.data)
    return OnboardingDraftResponse(**row)


@router.post("/complete", response_model=OnboardingCompleteResponse)
@limiter.limit("10/minute")
async def complete_onboarding(request: Request, response: Response, body: OnboardingComplete, user: AuthUser = Depends(get_current_user)):
    workspace = await get_container().organization_service.complete_onboarding(user=user, data=body)
    return OnboardingCompleteResponse(workspace=workspace)
