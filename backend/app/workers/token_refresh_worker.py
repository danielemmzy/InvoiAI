"""
============================================================
Token Refresh Worker

Flow 12 — proactive hourly sweep. Reactive refresh already
existed inside quickbooks_worker.py/xero_worker.py (refresh
right before a sync that needs it); this is the doc's separate
"scheduler fires every hour -> integration_connections WHERE
expires_at < now() + 2 hours -> refresh" sweep, so a connection
that just isn't due for a sync anytime soon doesn't silently
expire.

error_count > 3 -> deactivate + notify admin, per Flow 12.
============================================================
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.core.enum.database import IntegrationProvider
from app.core.enum.notification import NotificationType
from app.integrations.quickbooks.oauth import QuickBooksOAuth
from app.integrations.xero.oauth import XeroOAuth
from app.services.token_service import TokenService
from app.repositories.integration.integration_repository import (
    IntegrationConnectionRepository,
)
from app.repositories.organization.member_repository import MemberRepository
from app.services.notification.notification_service import NotificationService
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)

MAX_ERROR_COUNT = 3
REFRESH_WINDOW_HOURS = 2


class TokenRefreshWorker(BaseWorker):
    def __init__(
        self,
        *,
        connection_repository: IntegrationConnectionRepository | None = None,
        member_repository: MemberRepository | None = None,
        notification_service: NotificationService | None = None,
        quickbooks_oauth: QuickBooksOAuth | None = None,
        xero_oauth: XeroOAuth | None = None,
        token_service: TokenService | None = None,
    ) -> None:
        super().__init__()
        self.connections = connection_repository or IntegrationConnectionRepository()
        self.members = member_repository or MemberRepository()
        self.notifications = notification_service or NotificationService()
        self.quickbooks_oauth = quickbooks_oauth or QuickBooksOAuth()
        self.xero_oauth = xero_oauth or XeroOAuth()
        self.tokens = token_service or TokenService(repository=self.connections)

    async def run(self) -> dict:
        """
        Zero-arg entrypoint — the scheduler calls this hourly
        directly (no per-connection fan-out needed to invoke it,
        unlike the OCR/analysis workers, since this worker already
        loops connections internally).
        """
        refreshed = 0
        failed = 0
        deactivated = 0

        for provider in (IntegrationProvider.QUICKBOOKS, IntegrationProvider.XERO):
            connections = await self.connections.list_active_connections(provider)

            for connection in connections:
                if not self._due_for_refresh(connection):
                    continue

                try:
                    await self._refresh_connection(provider, connection)
                    refreshed += 1
                except Exception as exc:
                    failed += 1
                    logger.exception(
                        "Token refresh failed for connection %s (%s)",
                        connection.id,
                        provider,
                    )
                    was_deactivated = await self._record_failure(connection, exc)
                    if was_deactivated:
                        deactivated += 1

        return {
            "refreshed": refreshed,
            "failed": failed,
            "deactivated": deactivated,
        }

    @staticmethod
    def _due_for_refresh(connection) -> bool:
        expires_at = getattr(connection, "expires_at", None)
        if expires_at is None:
            return False

        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                return False

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        return expires_at < datetime.now(UTC) + timedelta(hours=REFRESH_WINDOW_HOURS)

    async def _refresh_connection(self, provider: IntegrationProvider, connection) -> None:
        oauth = (
            self.quickbooks_oauth
            if provider == IntegrationProvider.QUICKBOOKS
            else self.xero_oauth
        )

        await self.tokens.refresh_connection(
            connection=connection,
            oauth=oauth,
        )
        await self.connections.clear_error(connection.id)

    async def _record_failure(self, connection, exc: Exception) -> bool:
        error_count = (connection.error_count or 0) + 1

        await self.connections.record_error(
            connection.id,
            str(exc),
            error_count,
        )

        if error_count > MAX_ERROR_COUNT:
            await self.connections.deactivate_connection(connection.id)
            await self._notify_disconnected(connection)
            return True

        return False

    async def _notify_disconnected(self, connection) -> None:
        owner = await self.members.get_owner(connection.org_id)
        if not owner:
            return

        owner_id = getattr(owner, "user_id", None) or getattr(owner, "id", None)
        if not owner_id:
            return

        await self.notifications.send(
            user_id=owner_id,
            organization_id=connection.org_id,
            type=NotificationType.INTEGRATION_ERROR
            if hasattr(NotificationType, "INTEGRATION_ERROR")
            else NotificationType.INSIGHT_CRITICAL,
            title=f"{connection.provider.value.title()} disconnected",
            message=(
                f"Your {connection.provider.value} connection was "
                f"disabled after repeated token refresh failures. "
                f"Reconnect it in Integrations to resume syncing."
            ),
        )
