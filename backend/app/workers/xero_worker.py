from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.integrations.xero.sync_service import XeroSyncService
from app.repositories.integration.integration_repository import IntegrationConnectionRepository
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class XeroWorker(BaseWorker):
    """Orchestrates Xero synchronization; sync logic lives in the service."""

    def __init__(
        self,
        *,
        sync_service_factory: Callable[..., XeroSyncService] = XeroSyncService,
        integration_repository: IntegrationConnectionRepository | None = None,
    ) -> None:
        super().__init__()
        self.sync_service_factory = sync_service_factory
        self.connections = integration_repository or IntegrationConnectionRepository()

    async def run(self, *, org_id: UUID) -> dict:
        service = self.sync_service_factory(org_id=org_id)
        return await service.sync()

    async def run_pending(self, *, limit: int = 50) -> dict[str, int]:
        connections = await self.connections.list_active_connections(IntegrationProvider.XERO)
        processed = 0
        failed = 0
        for connection in connections[:limit]:
            try:
                await self.execute(org_id=connection.org_id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("Xero sync failed for connection %s", connection.id)
        return {"processed": processed, "failed": failed}
