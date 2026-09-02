from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.integrations.quickbooks.client import QuickBooksClient
from app.repositories.ap.chart_of_accounts_repository import ChartOfAccountRepository
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class QuickBooksChartOfAccountsSync:
    """Synchronize QuickBooks Account records into InvoiAI's tenant COA.

    PostgreSQL remains the source of truth for the local coding engine.
    QuickBooks is the source of truth for accounts imported from QuickBooks.
    The sync is idempotent on (org_id, external_id).
    """

    PAGE_SIZE = 1000

    def __init__(self, *, org_id: UUID, realm_id: str) -> None:
        self.org_id = org_id
        self.client = QuickBooksClient(org_id=org_id, realm_id=realm_id)
        self.repository = ChartOfAccountRepository()

    @staticmethod
    def _map_account(account: dict[str, Any]) -> dict[str, Any]:
        external_id = str(account["Id"])
        account_code = (account.get("AcctNum") or external_id).strip()
        account_name = (account.get("Name") or account_code).strip()
        account_type = (account.get("AccountType") or "other").strip().lower()
        subtype = account.get("AccountSubType")
        parent_ref = account.get("ParentRef") or {}
        return {
            "external_id": external_id,
            "account_code": account_code,
            "account_name": account_name,
            "account_type": account_type,
            "account_subtype": subtype,
            "external_parent_id": (
                str(parent_ref["value"]) if parent_ref.get("value") else None
            ),
            "is_active": bool(account.get("Active", True)),
            # A QuickBooks sub-account is normally a parent/container.
            "is_postable": not bool(account.get("SubAccount", False)),
            "source": "quickbooks",
            "_parent_external_id": str(parent_ref["value"]) if parent_ref.get("value") else None,
        }

    async def sync(self) -> dict[str, int]:
        records: list[dict[str, Any]] = []
        start = 1

        while True:
            response = await self.client.accounts(
                start_position=start,
                max_results=self.PAGE_SIZE,
            )
            page = (response.get("QueryResponse") or {}).get("Account") or []
            records.extend(page)
            if len(page) < self.PAGE_SIZE:
                break
            start += self.PAGE_SIZE

        mapped = [self._map_account(item) for item in records]
        if not mapped:
            return {"total": 0, "imported": 0, "updated": 0, "deactivated": 0}


        for item in mapped:
            item.pop("_parent_external_id", None)

        before = {
            row.external_id
            for row in await self.repository.list_by_org(self.org_id, active_only=False)
            if row.external_id
        }

        await self.repository.upsert_from_erp(self.org_id, mapped)

        # Resolve the whole hierarchy in one database statement instead of
        # issuing one UPDATE per account.
        await self.repository.resolve_parents(self.org_id)

        current_ids = {str(item["external_id"]) for item in mapped if item.get("external_id")}
        stale = before - current_ids
        if stale:
            await self.repository.deactivate_external_ids(
                self.org_id,
                list(stale),
            )

        imported = len(current_ids - before)
        updated = len(current_ids & before)
        try:
            redis = await get_redis()
            await redis.delete(f"invoiai:coa:v1:{self.org_id}")
        except Exception:
            # Cache is non-critical; the database is authoritative.
            pass
        return {
            "total": len(mapped),
            "imported": imported,
            "updated": updated,
            "deactivated": len(stale),
        }
