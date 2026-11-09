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

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_verified_user
from pydantic import BaseModel

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.container import get_container
from app.core.enum.database import ApprovalDecision
from app.core.ocm import get_org_context
from app.core.permissions import APPROVE_DOCUMENTS, VIEW_APPROVALS
from app.schemas.approval import ApprovalQueueResponse
from app.services.approval.approval_step_service import ApprovalStepService


router = APIRouter(
    prefix="/approvals",
    tags=["Approvals"],
    dependencies=[Depends(require_verified_user)],
)


def _step_service() -> ApprovalStepService:
    return get_container().approval_step_service


def _workflow_repository():
    return get_container().approval_workflow_repository


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approved" | "rejected"
    comment: str | None = None


@router.get(
    "",
    response_model=list[ApprovalQueueResponse],
)
async def list_pending_approvals(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if VIEW_APPROVALS not in ctx.permissions:
        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    rows = await _workflow_repository().approval_queue_for_user(
        ctx.org_id,
        user.id,
    )

    return [
        ApprovalQueueResponse.model_validate(row)
        for row in rows
    ]


@router.get(
    "/overdue",
    response_model=list[ApprovalQueueResponse],
)
async def list_overdue_approvals(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if APPROVE_DOCUMENTS not in ctx.permissions:
        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    rows = await _workflow_repository().approval_queue_for_user(
        ctx.org_id,
        user.id,
    )

    now = datetime.now(timezone.utc)

    overdue = [
        row
        for row in rows
        if row.get("due_date")
        and datetime.fromisoformat(
            str(row["due_date"]).replace("Z", "+00:00")
        ) < now
    ]

    return [
        ApprovalQueueResponse.model_validate(row)
        for row in overdue
    ]


@router.get(
    "/document/{document_id}/history",
)
async def get_document_approval_history(
    document_id: UUID,
    ctx: OrganizationContext = Depends(get_org_context),
):
    """
    Every approval workflow (bill and/or payment) for a document,
    each with its steps and its immutable approval_history events —
    the timeline the document page renders.

    The organization permission is checked through the organization
    context rather than a non-existent require_permission dependency.
    """

    if VIEW_APPROVALS not in ctx.permissions:
        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    container = get_container()

    workflow_repo = container.approval_workflow_repository
    step_repo = container.approval_step_repository
    history_repo = container.approval_history_repository

    from app.core.supabase import get_supabase

    rows = (
        get_supabase()
        .table("approval_workflows")
        .select("*")
        .eq("org_id", str(ctx.org_id))
        .eq("document_id", str(document_id))
        .order("initiated_at")
        .execute()
        .data
        or []
    )

    result = []

    for row in rows:
        workflow_id = UUID(row["id"])

        steps = await step_repo.list_workflow_steps(
            workflow_id
        )

        history = await history_repo.list_workflow_history(
            workflow_id
        )

        result.append(
            {
                "workflow": row,
                "steps": [
                    step.model_dump(mode="json")
                    for step in sorted(
                        steps,
                        key=lambda step: step.step_number,
                    )
                ],
                "history": [
                    event.model_dump(mode="json")
                    for event in history
                ],
            }
        )

    return result


@router.post(
    "/{step_id}/decide",
)
async def decide_approval_step(
    step_id: UUID,
    payload: ApprovalDecisionRequest,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    """
    Routes every decision through the canonical ApprovalEngine
    (app/services/approval/approval_engine.py), which is the single
    place that validates the actor/current-step/pending-state,
    persists the decision, writes approval_history + audit_logs,
    and advances (or completes/rejects) the workflow.

    This replaced a call into ApprovalStepService, which recorded
    a step's decision but never advanced the workflow to the next
    step — the actual root cause of approval steps appearing
    "stuck" after step 1.
    """

    if APPROVE_DOCUMENTS not in ctx.permissions:
        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    if payload.decision not in (
        "approved",
        "rejected",
    ):
        raise HTTPException(
            status_code=400,
            detail="decision must be 'approved' or 'rejected'",
        )

    decision = ApprovalDecision(payload.decision)

    container = get_container()

    step_repository = container.approval_step_repository

    existing_step = await step_repository.get_step(
        step_id,
    )

    if existing_step is None:
        raise HTTPException(
            status_code=404,
            detail="Approval step not found.",
        )

    if str(existing_step.org_id) != str(ctx.org_id):
        raise HTTPException(
            status_code=404,
            detail="Approval step not found.",
        )

    try:
        await container.approval_engine.process_decision(
            workflow_id=existing_step.workflow_id,
            step_id=step_id,
            actor_id=user.id,
            decision=decision,
            comment=payload.comment,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    step = await step_repository.get_step(
        step_id,
    )

    # Keep the legacy approval response unchanged, but synchronize
    # the AP state machine when this step belongs to an
    # AP-automation document.
    try:
        from app.core.supabase import get_supabase
        from app.services.ap.approval_bridge import APApprovalBridge

        row = (
            get_supabase()
            .table("approval_steps")
            .select("workflow_id")
            .eq("id", str(step_id))
            .limit(1)
            .execute()
            .data
        )

        if row:
            workflow = (
                get_supabase()
                .table("approval_workflows")
                .select("document_id")
                .eq("id", row[0]["workflow_id"])
                .limit(1)
                .execute()
                .data
            )

            if workflow:
                await APApprovalBridge().sync_after_decision(
                    workflow_id=UUID(
                        row[0]["workflow_id"]
                    ),
                    document_id=UUID(
                        workflow[0]["document_id"]
                    ),
                    actor_id=user.id,
                )

    except Exception:
        # Do not break the existing approval endpoint if AP
        # metadata is not installed.
        pass

    if step is None:
        raise HTTPException(
            status_code=404,
            detail="Approval step not found after decision.",
        )

    return step.model_dump(
        mode="json",
    )