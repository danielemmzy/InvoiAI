from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.repositories.integration.integration_repository import IntegrationConnectionRepository
from app.integrations.quickbooks.sync_service import QuickBooksSyncService
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class QuickBooksWorker(BaseWorker):
    """Orchestrates QuickBooks synchronization; sync logic lives in the service."""

    def __init__(
        self,
        *,
        sync_service_factory: Callable[..., QuickBooksSyncService] = QuickBooksSyncService,
        integration_repository: IntegrationConnectionRepository | None = None,
    ) -> None:
        super().__init__()
        self.sync_service_factory = sync_service_factory
        self.connections = integration_repository or IntegrationConnectionRepository()

    async def run(self, *, org_id: UUID, realm_id: str) -> dict:
        service = self.sync_service_factory(org_id=org_id, realm_id=realm_id)
        return await service.sync()

    async def run_pending(self, *, limit: int = 50) -> dict[str, int]:
        connections = await self.connections.list_active_connections(IntegrationProvider.QUICKBOOKS)
        processed = 0
        failed = 0
        for connection in connections[:limit]:
            try:
                await self.execute(org_id=connection.org_id, realm_id=connection.realm_id or "")
                processed += 1
            except Exception:
                failed += 1
                logger.exception("QuickBooks sync failed for connection %s", connection.id)
        return {"processed": processed, "failed": failed}
