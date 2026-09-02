from __future__ import annotations

import logging
from app.core.enum.database import IntegrationProvider
from app.repositories.integration.integration_repository import IntegrationConnectionRepository
from app.services.ap.chart_of_accounts_service import ChartOfAccountsService

logger = logging.getLogger(__name__)


class ChartOfAccountsSyncWorker:
    """Refresh active QuickBooks account lists on a low-frequency schedule."""

    async def run(self, limit: int = 100) -> dict:
        repo = IntegrationConnectionRepository()
        connections = await repo.list_active_connections(IntegrationProvider.QUICKBOOKS)
        service = ChartOfAccountsService()
        processed = failed = 0
        for connection in connections[:limit]:
            if not connection.realm_id:
                continue
            try:
                await service.sync_from_quickbooks(connection.org_id, connection.realm_id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("COA sync failed for org %s", connection.org_id)
        return {"processed": processed, "failed": failed}
