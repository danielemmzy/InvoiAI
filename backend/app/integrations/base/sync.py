from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from app.integrations.base.client import BaseAPIClient
from app.integrations.base.mapper import BaseIntegrationMapper


class BaseSyncService(ABC):
    """
    Base synchronization service.

    Provider implementations only define:

    • fetch()
    • map()
    • persist()

    Everything else is shared.
    """

    def __init__(
        self,
        *,
        client: BaseAPIClient,
        mapper: BaseIntegrationMapper,
    ) -> None:

        self.client = client
        self.mapper = mapper

    # =====================================================
    # Public API
    # =====================================================

    async def sync(self) -> dict[str, int]:

        imported = 0
        updated = 0
        skipped = 0
        failed = 0

        records = await self.fetch()

        for payload in records:

            try:

                model = await self.map(payload)

                if model is None:
                    skipped += 1
                    continue

                created = await self.persist(
                    model=model,
                    payload=payload,
                )

                if created:
                    imported += 1
                else:
                    updated += 1

            except Exception:
                failed += 1

        return {
            "total": len(records),
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }

    # =====================================================
    # Hooks
    # =====================================================

    @abstractmethod
    async def fetch(self) -> list[dict[str, Any]]:
        """
        Download provider records.
        """

    async def map(
        self,
        payload: dict[str, Any],
    ):
        """
        Default mapper.

        Override when foreign keys
        (vendor/document lookups)
        are required.
        """

        return self.mapper.to_domain(payload)

    @abstractmethod
    async def persist(
        self,
        *,
        model,
        payload: dict[str, Any],
    ) -> bool:
        """
        Persist mapped model.

        Returns:
            True  -> created
            False -> updated
        """