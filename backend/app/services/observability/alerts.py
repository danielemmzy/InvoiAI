"""Incident alert delivery.

Alerts are structured events with a named owner and a runbook link. Delivery
uses the configured webhook when present; otherwise the alert is logged so the
runbook path still works. No customer payloads or secrets are sent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.observability import redact


@dataclass(frozen=True)
class Alert:
    name: str
    severity: str
    summary: str
    runbook: str
    owner: str | None = None


ALERT_RUNBOOKS: dict[str, str] = {
    "worker_stuck": "docs/OPERATOR_RUNBOOKS.md#stuck-workers",
    "provider_outage": "docs/OPERATOR_RUNBOOKS.md#provider-outage",
    "webhook_lag": "docs/OPERATOR_RUNBOOKS.md#webhook-replay",
    "restore": "docs/OPERATOR_RUNBOOKS.md#backup-restore",
    "data_deletion": "docs/OPERATOR_RUNBOOKS.md#customer-data-deletion",
    "secret_rotation": "docs/OPERATOR_RUNBOOKS.md#secret-rotation",
    "quota_exhausted": "docs/OPERATOR_RUNBOOKS.md#quota-and-allowance",
}


class AlertService:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def send(self, alert: Alert) -> dict:
        payload = {
            "name": alert.name,
            "severity": alert.severity,
            "summary": redact(alert.summary),
            "runbook": alert.runbook,
            "owner": alert.owner or settings.alert_owner,
            "occurred_at": datetime.now(UTC).isoformat(),
            "service": "invoiai-backend",
        }

        logger.warning("alert", extra={"alert": payload})

        if not settings.alert_webhook_url:
            return {"delivered": False, "reason": "alert_webhook_not_configured", "alert": payload}

        try:
            async with httpx.AsyncClient(
                timeout=10, transport=self.transport
            ) as client:
                response = await client.post(settings.alert_webhook_url, json=payload)
            response.raise_for_status()
        except Exception as exc:
            logger.exception("alert_delivery_failed", alert=alert.name)
            return {
                "delivered": False,
                "reason": "alert_webhook_failed",
                "error": str(exc)[:200],
                "alert": payload,
            }

        return {"delivered": True, "status_code": response.status_code, "alert": payload}
