"""
============================================================
Copilot Router

Flow 7 — POST /api/v1/copilot/chat, GET /sessions,
GET /sessions/{id}.

CopilotService already existed fully built (tool-calling loop,
cost tracking, response parsing) but had no HTTP entrypoint.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context
from app.repositories.ai.chat_repository import ChatRepository
from app.core.container import get_container
from app.core.limiter import limiter
from app.core.authorization import require_permission
from app.core.permissions import RUN_AI, VIEW_AI
from app.services.ai.copilot_service import CopilotService

router = APIRouter(prefix="/copilot", tags=["Copilot"])


class ChatRequest(BaseModel):
    session_id: UUID | None = None
    message: str


@router.post("/chat")
@limiter.limit("30/minute")
async def send_chat_message(
    response: Response,
    request: Request,
    payload: ChatRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(RUN_AI)),
):
    """
    Flow 7: "chat_sessions fetched OR created" — if no session_id
    is supplied, a new session is created here before delegating
    to CopilotService, which requires an existing session.
    """
    chat_repository = get_container().chat_repository

    session_id = payload.session_id
    if session_id is None:
        session = await chat_repository.create_session(
            {
                "org_id": ctx.org_id,
                "user_id": user.id,
                "title": payload.message[:60],
                "is_active": True,
                "total_messages": 0,
            }
        )
        session_id = session.id

    result = await get_container().copilot_service.send_message(
        session_id=session_id,
        org_id=ctx.org_id,
        user_id=user.id,
        message=payload.message,
        personal_mode=ctx.feature_flags.get("personal_mode", False),
    )

    return {"session_id": str(session_id), **result}


@router.get("/sessions")
async def list_sessions(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_AI)),
):
    sessions = await get_container().chat_repository.list_org_sessions(ctx.org_id)
    sessions = [s for s in sessions if s.user_id == user.id]
    return [s.model_dump(mode="json") for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_AI)),
):
    repository = get_container().chat_repository

    session = await repository.get_session(session_id)
    if (
        session is None
        or session.org_id != ctx.org_id
        or session.user_id != user.id
    ):
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await repository.list_session_messages(session_id)

    return {
        "session": session.model_dump(mode="json"),
        "messages": [m.model_dump(mode="json") for m in messages],
    }
