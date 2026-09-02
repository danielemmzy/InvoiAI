from __future__ import annotations

import logging
from typing import Any

from app.core.container import get_container
from app.workers.quickbooks_worker import QuickBooksWorker
from app.workers.xero_worker import XeroWorker

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Route normalized integration webhook events to their application services."""

    def __init__(self, *, stripe_processor=None) -> None:
        self.quickbooks_worker = QuickBooksWorker()
        self.xero_worker = XeroWorker()
        self.stripe_processor = stripe_processor or get_container().stripe_event_processor

    async def dispatch(self, *, event: dict[str, Any]) -> None:
        provider = event.get("provider")
        if provider == "quickbooks":
            await self._quickbooks(event)
        elif provider == "xero":
            await self._xero(event)
        elif provider == "stripe":
            await self._stripe(event)
        elif provider == "google":
            await self._google(event)
        else:
            logger.warning("Unknown webhook provider: %s", provider)

    async def _quickbooks(self, event: dict[str, Any]) -> None:
        await self.quickbooks_worker.execute(
            org_id=event.get("org_id"),
            realm_id=event.get("realm_id"),
        )

    async def _xero(self, event: dict[str, Any]) -> None:
        await self.xero_worker.execute(org_id=event.get("org_id"))

    async def _stripe(self, event: dict[str, Any]) -> None:
        await self.stripe_processor.process(event)

    async def _google(self, event: dict[str, Any]) -> None:
        logger.info("Google webhook received.")
