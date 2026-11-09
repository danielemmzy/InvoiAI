from __future__ import annotations

import logging
from uuid import UUID

from app.core.enum.ap import InvoiceAPStatus
from app.core.observability import record_provider_sync
from app.core.supabase import get_supabase
from app.services.ap.bill_sync_service import BillSyncService
from app.services.ap.provider.accounting_provider import get_accounting_provider
from app.services.payment.payment_authorization_service import (
    PaymentAuthorizationService,
)
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class BillSyncWorker(BaseWorker):
    name = "bill-sync-worker"

    def __init__(self, db=None):
        super().__init__()
        self.db = db or get_supabase()
        self.service = BillSyncService(self.db)

    async def run(self, *, document_id: UUID):
        rows = (
            self.db.table("documents")
            .select("org_id,ap_status,ap_enabled,erp_bill_id")
            .eq("id", str(document_id))
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return {"status": "not_found"}

        doc = rows[0]
        if (
            not bool(doc.get("ap_enabled"))
            or doc.get("ap_status") != InvoiceAPStatus.APPROVED.value
        ):
            if doc.get("erp_bill_id"):
                return {
                    "status": "already_synced",
                    "erp_bill_id": doc["erp_bill_id"],
                }
            return {"status": "not_eligible"}

        # Compare-and-set status claim: only one worker can move APPROVED -> SYNCING.
        claimed = (
            self.db.table("documents")
            .update(
                {
                    "ap_status": InvoiceAPStatus.SYNCING_TO_ERP.value,
                    "erp_sync_started_at": "now()",
                    "erp_sync_error": None,
                }
            )
            .eq("id", str(document_id))
            .eq("org_id", str(doc["org_id"]))
            .eq("ap_status", InvoiceAPStatus.APPROVED.value)
            .select("id")
            .execute()
            .data
            or []
        )
        if not claimed:
            return {"status": "already_claimed"}

        provider = None
        try:
            provider = await get_accounting_provider(UUID(doc["org_id"]), self.db)
            external_id = await provider.create_bill(
                org_id=UUID(doc["org_id"]), document_id=document_id
            )
            record_provider_sync(provider=provider.name, result="success")
            if not external_id:
                raise RuntimeError("Accounting provider returned no bill ID.")

            # Existing provider service persists erp_bill_id and transitions to
            # PAYMENT_READY. Re-read instead of attempting a second
            # compare-and-set against SYNCING_TO_ERP: the adapter may persist
            # before returning, so a second CAS would falsely fail.
            confirmed = (
                self.db.table("documents")
                .select("erp_bill_id,ap_status")
                .eq("id", str(document_id))
                .eq("org_id", str(doc["org_id"]))
                .single()
                .execute()
                .data
            )
            if not confirmed.get("erp_bill_id") or str(
                confirmed.get("erp_bill_id")
            ) != str(external_id):
                raise RuntimeError(
                    "ERP bill was created but local confirmation could not be "
                    "verified; reconcile before retrying."
                )
            (
                self.db.table("documents")
                .update(
                    {
                        "erp_sync_started_at": None,
                        "erp_sync_error": None,
                        "erp_sync_attempts": 0,
                    }
                )
                .eq("id", str(document_id))
                .eq("org_id", str(doc["org_id"]))
                .execute()
            )
        except Exception as exc:
            record_provider_sync(
                provider=getattr(provider, "name", "unknown"), result="failed"
            )
            # A timeout after the provider accepted the create is not proof of
            # failure. If the adapter persisted an ERP bill id before the
            # exception, adopt it instead of retrying and risking a duplicate.
            adopted = (
                self.db.table("documents")
                .select("erp_bill_id,ap_status")
                .eq("id", str(document_id))
                .eq("org_id", str(doc["org_id"]))
                .limit(1)
                .execute()
                .data
                or []
            )
            if adopted and adopted[0].get("erp_bill_id"):
                external_id = adopted[0]["erp_bill_id"]
                (
                    self.db.table("documents")
                    .update(
                        {
                            "erp_sync_started_at": None,
                            "erp_sync_error": None,
                            "erp_sync_attempts": 0,
                        }
                    )
                    .eq("id", str(document_id))
                    .eq("org_id", str(doc["org_id"]))
                    .execute()
                )
            else:
                (
                    self.db.table("documents")
                    .update(
                        {
                            "ap_status": InvoiceAPStatus.APPROVED.value,
                            "erp_sync_started_at": None,
                            "erp_sync_error": str(exc)[:1000],
                        }
                    )
                    .eq("id", str(document_id))
                    .eq("org_id", str(doc["org_id"]))
                    .eq("ap_status", InvoiceAPStatus.SYNCING_TO_ERP.value)
                    .execute()
                )
                raise

        try:
            await PaymentAuthorizationService(self.db).evaluate(
                org_id=UUID(doc["org_id"]), document_id=document_id
            )
        except Exception:
            logger.exception(
                "Payment authorization evaluation failed for %s", document_id
            )

        return {
            "status": "payment_ready",
            "erp_bill_id": external_id,
            "payment_released": False,
        }

    async def run_pending(self, limit: int = 25):
        rows = (
            self.db.table("documents")
            .select("id")
            .eq("ap_enabled", True)
            .eq("ap_status", InvoiceAPStatus.APPROVED.value)
            .eq("document_type", "invoice")
            .is_("erp_bill_id", None)
            .limit(limit)
            .execute()
            .data
            or []
        )
        done = failed = 0
        for row in rows:
            try:
                await self.execute(document_id=UUID(row["id"]))
                done += 1
            except Exception:
                failed += 1
                logger.exception("Bill sync failed for %s", row["id"])
        return {"processed": done, "failed": failed}
