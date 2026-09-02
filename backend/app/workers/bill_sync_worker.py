from __future__ import annotations
import logging
from uuid import UUID
from app.core.supabase import get_supabase
from app.core.enum.ap import InvoiceAPStatus
from app.services.ap.bill_sync_service import BillSyncService
from app.workers.base import BaseWorker
logger=logging.getLogger(__name__)
class BillSyncWorker(BaseWorker):
    name="bill-sync-worker"
    def __init__(self,db=None): super().__init__(); self.db=db or get_supabase(); self.service=BillSyncService(self.db)
    async def run(self, *, document_id: UUID):
        doc=self.db.table("documents").select("org_id,ap_status").eq("id",str(document_id)).single().execute().data
        if not doc or doc.get("ap_status")!=InvoiceAPStatus.APPROVED.value:return
        self.db.table("documents").update({"ap_status":InvoiceAPStatus.SYNCING_TO_ERP.value}).eq("id",str(document_id)).execute()
        try: await self.service.push_to_quickbooks(org_id=UUID(doc["org_id"]),document_id=document_id)
        except Exception:
            self.db.table("documents").update({"ap_status":InvoiceAPStatus.APPROVED.value}).eq("id",str(document_id)).execute(); raise
    async def run_pending(self,limit:int=25):
        rows=self.db.table("documents").select("id").eq("ap_status",InvoiceAPStatus.APPROVED.value).eq("document_type","invoice").is_("erp_bill_id",None).limit(limit).execute().data or []
        done=failed=0
        for row in rows:
            try: await self.execute(document_id=UUID(row["id"])); done+=1
            except Exception: failed+=1; logger.exception("Bill sync failed for %s",row["id"])
        return {"processed":done,"failed":failed}
