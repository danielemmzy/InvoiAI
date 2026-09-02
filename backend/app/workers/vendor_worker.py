from __future__ import annotations

import logging
from uuid import UUID

from app.services.vendor.vendor_memory_service import VendorMemoryService
from app.repositories.document.vendor_repository import VendorRepository
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class VendorWorker(BaseWorker):
    """
    Background vendor worker.

    Responsibilities
    ----------------
    • Refresh vendor AI memory
    • Refresh vendor intelligence
    • Retry failed AI jobs

    No AI logic.
    No persistence logic.

    Delegates everything to VendorMemoryService.
    """

    name = "vendor-worker"

    def __init__(
        self,
        *,
        vendor_memory_service: VendorMemoryService,
        vendor_repository: VendorRepository | None = None,
    ) -> None:

        super().__init__()

        self.vendor_memory_service = vendor_memory_service
        self.vendors = vendor_repository or VendorRepository()

    # =====================================================
    # Execute
    # =====================================================

    async def run(
        self,
        *,
        vendor_id: UUID,
    ) -> None:

        logger.info(
            "Refreshing AI memory for vendor %s",
            vendor_id,
        )

        await self.vendor_memory_service.update_memory(vendor_id)

        logger.info(
            "Vendor AI memory refreshed for %s",
            vendor_id,
        )

    async def run_pending(self, *, limit: int = 50) -> dict[str, int]:
        vendors = await self.vendors.list_all(limit=limit)
        processed = 0
        failed = 0
        for vendor in vendors:
            try:
                await self.execute(vendor_id=vendor.id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("Vendor memory refresh failed for %s", vendor.id)
        return {"processed": processed, "failed": failed}
