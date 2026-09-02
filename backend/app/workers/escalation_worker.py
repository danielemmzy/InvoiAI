from __future__ import annotations

import logging
from uuid import UUID

from app.core.enum.notification import NotificationType
from app.repositories.approval.step_repository import ApprovalStepRepository
from app.repositories.organization.organization_repository import OrganizationRepository
from app.services.approval.approval_step_service import ApprovalStepService
from app.services.notification.notification_service import NotificationService
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class EscalationWorker(BaseWorker):
    """Escalates overdue approval steps through the approval service."""

    def __init__(
        self,
        *,
        step_service: ApprovalStepService,
        step_repository: ApprovalStepRepository | None = None,
        organization_repository: OrganizationRepository | None = None,
        notification_service: NotificationService,
    ) -> None:
        super().__init__()
        self.steps = step_service
        self.step_repository = step_repository or ApprovalStepRepository()
        self.organizations = organization_repository or OrganizationRepository()
        self.notifications = notification_service

    async def run(self, *, org_id: UUID) -> dict[str, int]:
        steps = await self.step_repository.list_overdue_steps(org_id)
        escalated = 0
        failed = 0
        for step in steps:
            try:
                updated = await self.steps.escalate(step_id=step.id)
                await self.notifications.send(
                    user_id=step.approver_id,
                    organization_id=step.org_id,
                    type=NotificationType.APPROVAL_ESCALATED,
                    title="Approval escalated",
                    message=f"Approval step '{step.step_name}' has been escalated.",
                    data={"workflow_id": str(step.workflow_id), "step_id": str(step.id)},
                )
                if updated:
                    escalated += 1
            except Exception:
                failed += 1
                logger.exception("Approval escalation failed for step %s", step.id)
        return {"escalated": escalated, "failed": failed}

    async def run_pending(self, *, limit: int = 1000) -> dict[str, int]:
        org_ids = await self.organizations.list_all_ids(limit=limit)
        escalated = failed = 0
        for org_id in org_ids:
            result = await self.run(org_id=org_id)
            escalated += result["escalated"]
            failed += result["failed"]
        return {"orgs_processed": len(org_ids), "escalated": escalated, "failed": failed}
