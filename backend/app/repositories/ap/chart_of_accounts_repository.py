from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.coa_mapper import ChartOfAccountMapper
from app.models.domain.ap import ChartOfAccount
class ChartOfAccountRepository(BaseRepository):
    table_name = "chart_of_accounts"
    mapper = ChartOfAccountMapper
    async def list_by_org(self, org_id: UUID, active_only: bool = True):
        q = self.table().select("*").eq("org_id", str(org_id))
        if active_only: q = q.eq("is_active", True)
        return self._many(q.order("account_code").execute())
    async def get_by_id(self, org_id: UUID, account_id: UUID):
        return self._one(self.table().select("*").eq("org_id", str(org_id)).eq("id", str(account_id)).limit(1).execute())
    async def get_by_code(self, org_id: UUID, code: str):
        return self._one(self.table().select("*").eq("org_id", str(org_id)).eq("account_code", code).limit(1).execute())
    async def upsert_from_erp(self, org_id: UUID, rows: list[dict]) -> int:
        if not rows:
            return 0
        payload = []
        for row in rows:
            item = dict(row)
            item["org_id"] = str(org_id)
            payload.append(item)
        self.table().upsert(payload, on_conflict="org_id,external_id").execute()
        return len(payload)

    async def raw_by_org(self, org_id: UUID) -> list[dict]:
        response = (
            self.table()
            .select("id,external_id")
            .eq("org_id", str(org_id))
            .execute()
        )
        return response.data or []

    async def resolve_parents(self, org_id: UUID) -> int:
        response = self.db.rpc(
            "resolve_quickbooks_coa_parents",
            {"p_org_id": str(org_id)},
        ).execute()
        return int(response.data or 0)

    async def set_parent(self, org_id: UUID, account_id: UUID, parent_id: UUID) -> None:
        (
            self.table()
            .update({"parent_account_id": str(parent_id)})
            .eq("org_id", str(org_id))
            .eq("id", str(account_id))
            .execute()
        )

    async def deactivate_external_ids(self, org_id: UUID, external_ids: list[str]) -> None:
        if not external_ids:
            return
        (
            self.table()
            .update({"is_active": False})
            .eq("org_id", str(org_id))
            .eq("source", "quickbooks")
            .in_("external_id", external_ids)
            .execute()
        )
