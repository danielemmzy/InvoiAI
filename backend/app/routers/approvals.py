"""
============================================================
Approvals Router

Flow 4 — GET /api/v1/approvals, POST /{step_id}/decide.

services/approval/* already existed fully built (workflow,
step, history services + repositories) but had no HTTP
entrypoint — this is that entrypoint.

SECURITY / CORRECTNESS FIX (see SECURITY_FIXES_APPLIED.md item #3):
list_pending_approvals previously called
ApprovalStepService.list_approver_tasks(), which returns bare
ApprovalStep rows — no vendor name, amount, currency, health
score, or risk level. The approval_queue Postgres view already
exists (workflow_repository.py: QUEUE_VIEW = "approval_queue")
and the ApprovalQueueResponse schema was already written to match
it (schemas/approval.py, "Mirrors approval_queue view") — nothing
was actually wired to call it. This now reads that view and
returns ApprovalQueueResponse rows, filtered to the current
approver, which is what the frontend approvals queue expects.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.ocm import get_org_context
from app.core.permissions import APPROVE_DOCUMENTS, VIEW_APPROVALS
from app.core.container import get_container
from app.services.approval.approval_step_service import ApprovalStepService
from app.schemas.approval import ApprovalQueueResponse

router = APIRouter(prefix="/approvals", tags=["Approvals"])


def _step_service() -> ApprovalStepService:
    return get_container().approval_step_service


def _workflow_repository():
    return get_container().approval_workflow_repository


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approved" | "rejected"
    comment: str | None = None


@router.get("", response_model=list[ApprovalQueueResponse])
async def list_pending_approvals(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if VIEW_APPROVALS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    rows = await _workflow_repository().approval_queue(ctx.org_id)
    mine = [row for row in rows if str(row.get("approver_id")) == str(user.id)]
    return [ApprovalQueueResponse.model_validate(row) for row in mine]


@router.get("/overdue", response_model=list[ApprovalQueueResponse])
async def list_overdue_approvals(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if APPROVE_DOCUMENTS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    from datetime import datetime, timezone

    rows = await _workflow_repository().approval_queue(ctx.org_id)
    now = datetime.now(timezone.utc)
    overdue = [
        row for row in rows
        if row.get("due_date") and datetime.fromisoformat(str(row["due_date"]).replace("Z", "+00:00")) < now
    ]
    return [ApprovalQueueResponse.model_validate(row) for row in overdue]


@router.post("/{step_id}/decide")
async def decide_approval_step(
    step_id: UUID,
    payload: ApprovalDecisionRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    """
    Flow 4: "OCM validates approver has APPROVE_DOCUMENTS
    permission" -> approve/reject -> audit_logs + approval_history
    entries (written inside the service layer's _apply_decision —
    see SECURITY_FIXES_APPLIED.md item #1).
    """
    if APPROVE_DOCUMENTS not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = _step_service()

    if payload.decision == "approved":
        step = await service.approve(
            step_id=step_id,
            approver_id=user.id,
            comment=payload.comment,
        )
    elif payload.decision == "rejected":
        step = await service.reject(
            step_id=step_id,
            approver_id=user.id,
            comment=payload.comment,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="decision must be 'approved' or 'rejected'",
        )

    # Keep the legacy approval response unchanged, but synchronize the AP
    # state machine when this step belongs to an AP-automation document.
    try:
        from app.core.supabase import get_supabase
        from app.services.ap.approval_bridge import APApprovalBridge
        row = get_supabase().table("approval_steps").select("workflow_id").eq("id", str(step_id)).limit(1).execute().data
        if row:
            workflow = get_supabase().table("approval_workflows").select("document_id").eq("id", row[0]["workflow_id"]).limit(1).execute().data
            if workflow:
                await APApprovalBridge().sync_after_decision(workflow_id=UUID(row[0]["workflow_id"]), document_id=UUID(workflow[0]["document_id"]), actor_id=user.id)
    except Exception:
        # Do not break the existing approval endpoint if AP metadata is not installed.
        pass
    return step.model_dump(mode="json")
