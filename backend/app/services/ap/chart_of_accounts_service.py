from __future__ import annotations

import json
from uuid import UUID

from app.core.redis import get_redis
from app.integrations.quickbooks.sync.chart_of_accounts_sync import QuickBooksChartOfAccountsSync
from app.repositories.ap.chart_of_accounts_repository import ChartOfAccountRepository

_CACHE_TTL = 60
_CACHE_PREFIX = "invoiai:coa:v1"


class ChartOfAccountsService:
    """Application service for tenant COA reads and ERP synchronization."""

    def __init__(self) -> None:
        self.repository = ChartOfAccountRepository()

    @staticmethod
    def _key(org_id: UUID, *, active_only: bool = True) -> str:
        scope = "active" if active_only else "all"
        return f"{_CACHE_PREFIX}:{org_id}:{scope}"

    @classmethod
    def _cache_keys(cls, org_id: UUID) -> tuple[str, str]:
        """Both cache scopes, so invalidation cannot leave a stale view behind."""
        return (
            cls._key(org_id, active_only=True),
            cls._key(org_id, active_only=False),
        )

    async def list(self, org_id: UUID, *, active_only: bool = True) -> list[dict]:
        key = self._key(org_id, active_only=active_only)
        try:
            redis = await get_redis()
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            # Cache is an optimization; PostgreSQL remains authoritative.
            pass

        rows = await self.repository.list_by_org(org_id, active_only=active_only)
        payload = [row.model_dump(mode="json") for row in rows]

        try:
            redis = await get_redis()
            await redis.setex(key, _CACHE_TTL, json.dumps(payload))
        except Exception:
            pass
        return payload

    async def invalidate(self, org_id: UUID) -> None:
        try:
            redis = await get_redis()
            await redis.delete(*self._cache_keys(org_id))
        except Exception:
            pass

    async def sync_from_quickbooks(self, org_id: UUID, realm_id: str) -> dict:
        result = await QuickBooksChartOfAccountsSync(
            org_id=org_id,
            realm_id=realm_id,
        ).sync()
        await self.invalidate(org_id)
        return result
