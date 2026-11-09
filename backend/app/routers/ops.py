"""/ops — read-only metrics and an alert-delivery test for operators."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.context import OrganizationContext
from app.core.authorization import require_permission
from app.core.observability import metrics, redact
from app.core.ocm import get_org_context
from app.core.permissions import VIEW_AUDIT_LOGS
from app.services.observability.alerts import ALERT_RUNBOOKS, Alert, AlertService

router = APIRouter(prefix="/ops", tags=["Operations"])


@router.get("/metrics")
async def metrics_snapshot(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_AUDIT_LOGS)),
):
    """In-process snapshot. A production collector should scrape this and
    forward it to the configured monitoring backend."""
    return redact(metrics.snapshot())


@router.post("/alerts/test")
async def send_test_alert(
    ctx: OrganizationContext = Depends(get_org_context),
    _: None = Depends(require_permission(VIEW_AUDIT_LOGS)),
):
    alert = Alert(
        name="test_alert",
        severity="info",
        summary="End-to-end alert delivery test from the operator console.",
        runbook=ALERT_RUNBOOKS["worker_stuck"],
    )
    return await AlertService().send(alert)
