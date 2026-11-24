from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.database import IntegrationProvider
from app.services.ap.provider.accounting_provider import NoActiveAccountingProviderError


from app.core.db import execute

class VendorImportService:
    """Dispatch supplier imports through the explicitly selected connection."""

    def __init__(self, db=None, provider_resolver=None) -> None:
        if db is None:
            from app.core.supabase import get_supabase

            db = get_supabase()
        self.db = db
        self.provider_resolver = provider_resolver or self._resolve_provider

    async def _resolve_provider(self, *, org_id: UUID, provider: str, db):
        rows = (
            (await execute(db.table("integration_connections").select("*")
            .eq("org_id", str(org_id)).eq("provider", provider)
            .eq("is_active", True).limit(1))).data
        )
        if not rows:
            raise NoActiveAccountingProviderError(
                f"No active {provider} connection for organization {org_id}."
            )
        connection = rows[0]
        if provider == IntegrationProvider.QUICKBOOKS.value:
            from app.integrations.quickbooks.sync.vendor_sync import QuickBooksVendorSync

            if not connection.get("realm_id"):
                raise NoActiveAccountingProviderError("The active QuickBooks connection has no selected company.")
            adapter = QuickBooksVendorSync(org_id=org_id, realm_id=connection["realm_id"])
            adapter.name = provider
            return adapter
        if provider == IntegrationProvider.XERO.value:
            from app.integrations.xero.sync.vendor_sync import XeroVendorSync

            if not connection.get("tenant_id"):
                raise NoActiveAccountingProviderError("The active Xero connection has no selected tenant.")
            adapter = XeroVendorSync(org_id=org_id)
            adapter.name = provider
            return adapter
        raise ValueError(f"Supplier import is not available for provider '{provider}'.")

    async def import_suppliers(self, *, org_id: UUID, provider: str) -> dict[str, int]:
        try:
            provider = IntegrationProvider(provider).value
        except ValueError as exc:
            raise ValueError("provider must be quickbooks, xero, or sage") from exc
        adapter = await self.provider_resolver(org_id=org_id, provider=provider, db=self.db)
        if adapter.name != provider:
            raise ValueError("Resolved accounting provider does not match the requested provider.")
        result = await adapter.sync()
        rows = (
            (await execute(self.db.table("integration_connections").select("id,metadata")
            .eq("org_id", str(org_id)).eq("provider", provider)
            .eq("is_active", True).limit(1))).data
        )
        if rows:
            connection = rows[0]
            counts = {key: result.get(key, 0) for key in ("total", "imported", "updated", "skipped", "failed")}
            completed_at = datetime.now(UTC).isoformat()
            metadata = dict(connection.get("metadata") or {})
            metadata["supplier_import"] = {
                "counts": counts,
                "errors": result.get("errors", []),
                "completed_at": completed_at,
            }
            (await execute(self.db.table("integration_connections").update({"metadata": metadata}).eq(
                "org_id", str(org_id)
            ).eq("id", str(connection["id"]))))
            result["completed_at"] = completed_at
        return result
