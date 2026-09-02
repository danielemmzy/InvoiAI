from __future__ import annotations

import logging
from uuid import UUID

from app.repositories.organization.organization_repository import OrganizationRepository
from app.services.insights.insight_service import InsightService
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class InsightWorker(BaseWorker):
    """Orchestrates organization-scoped insight generation."""

    def __init__(
        self,
        *,
        insight_service: InsightService | None = None,
        organization_repository: OrganizationRepository | None = None,
    ) -> None:
        super().__init__()
        self.service = insight_service or InsightService()
        self.organizations = organization_repository or OrganizationRepository()

    async def run(self, *, org_id: UUID) -> dict:
        return await self.service.generate(org_id=org_id)

    async def run_pending(self, *, limit: int = 1000) -> dict[str, int]:
        org_ids = await self.organizations.list_all_ids(limit=limit)
        processed = 0
        failed = 0
        for org_id in org_ids:
            try:
                await self.execute(org_id=org_id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("Insight generation failed for org %s", org_id)
        return {"orgs_processed": processed, "orgs_total": len(org_ids), "failed": failed}
