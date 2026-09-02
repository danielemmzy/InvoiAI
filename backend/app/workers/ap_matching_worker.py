from __future__ import annotations
import logging
from uuid import UUID
from app.core.supabase import get_supabase
from app.core.redis import get_redis
from app.core.enum.ap import InvoiceAPStatus, APMatchStatus
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.services.ap.matching_service import MatchingService
from app.workers.base import BaseWorker
logger=logging.getLogger(__name__)
class APMatchingWorker(BaseWorker):
    name="ap-matching-worker"
    def __init__(self,db=None): super().__init__(); self.db=db or get_supabase(); self.state=InvoiceStateMachine(self.db); self.service=MatchingService(self.db)
    async def run(self, *, document_id: UUID):
        redis = await get_redis()
        lock = redis.lock(f"invoiai:ap:matching:{document_id}", timeout=300, blocking=False)
        if not await lock.acquire():
            return
        try:
            return await self._run_once(document_id=document_id)
        finally:
            try:
                await lock.release()
            except Exception:
                logger.warning("Failed to release AP matching lock", exc_info=True)

    async def _run_once(self, *, document_id: UUID):
        doc=self.db.table("documents").select("*").eq("id",str(document_id)).single().execute().data
        if not doc or doc.get("document_type")!="invoice":
            return
        # AP automation is business-mode only. Personal finance documents
        # continue through the existing personal pipeline untouched.
        org = self.db.table("organizations").select("features").eq("id", str(doc["org_id"])).limit(1).execute().data
        features = (org[0].get("features") or {}) if org else {}
        if bool(features.get("personal_mode")):
            return
        if doc.get("ap_status") not in {InvoiceAPStatus.VALIDATING.value,InvoiceAPStatus.RECEIVED.value}: return
        await self.state.transition(document_id,UUID(doc["org_id"]),InvoiceAPStatus.MATCHING,triggered_by="worker")
        lines=self.db.table("document_line_items").select("*").eq("document_id",str(document_id)).order("position").execute().data or []
        po=None
        if doc.get("purchase_order_id"):
            rows=self.db.table("purchase_orders").select("*").eq("org_id",doc["org_id"]).eq("id",doc["purchase_order_id"]).limit(1).execute().data; po=rows[0] if rows else None
        result=await self.service.run(org_id=UUID(doc["org_id"]),document_id=document_id,document=doc,line_items=lines,purchase_order=po)
        if result.status==APMatchStatus.EXCEPTION:
            self.db.table("documents").update({"status":"needs_review","pipeline_stage":"approval"}).eq("id",str(document_id)).execute()
            await self.state.transition(document_id,UUID(doc["org_id"]),InvoiceAPStatus.MATCH_EXCEPTION,triggered_by="worker",reason=f"{len(result.exceptions)} matching exception(s)")
        else:
            await self.state.transition(document_id,UUID(doc["org_id"]),InvoiceAPStatus.CODING,triggered_by="worker")
    async def run_pending(self,limit:int=50):
        rows=self.db.table("documents").select("id").in_("ap_status",[InvoiceAPStatus.VALIDATING.value,InvoiceAPStatus.RECEIVED.value]).eq("document_type","invoice").limit(limit).execute().data or []
        done=failed=0
        for row in rows:
            try: await self.execute(document_id=UUID(row["id"])); done+=1
            except Exception: failed+=1; logger.exception("AP matching failed for %s",row["id"])
        return {"processed":done,"failed":failed}
