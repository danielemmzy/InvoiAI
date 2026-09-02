"""
============================================================
Memory Worker

Flow 3's "workers/memory_worker.py (runs later, low priority)
-> memory_service.update_vendor_memory(vendor_id)". This file
was previously empty (0 bytes) despite being registered on the
scheduler every 30 minutes, so every scheduled run would have
raised AttributeError on `MemoryWorker().run`.
============================================================
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.repositories.document.vendor_repository import VendorRepository
from app.services.vendor.vendor_memory_service import VendorMemoryService
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class MemoryWorker(BaseWorker):
    def __init__(
        self,
        *,
        vendor_repository: VendorRepository | None = None,
        memory_service: VendorMemoryService | None = None,
    ) -> None:
        super().__init__()
        self.vendors = vendor_repository or VendorRepository()
        self.memory_service = memory_service or VendorMemoryService(
            repository=self.vendors
        )

    async def run(self, *, vendor_id: UUID) -> dict:
        await self.memory_service.update_memory(vendor_id)
        return {"vendor_id": str(vendor_id), "status": "updated"}

    async def run_pending(self, limit: int = 50) -> dict:
        """Refresh a bounded global vendor-memory backlog."""
        candidates = await self.vendors.list_all(limit=limit)
        updated = 0
        failed = 0
        for vendor in candidates:
            try:
                await self.execute(vendor_id=vendor.id)
                updated += 1
            except Exception:
                failed += 1
                logger.exception("Memory update failed for vendor %s", vendor.id)
        return {"vendors_updated": updated, "failed": failed}
