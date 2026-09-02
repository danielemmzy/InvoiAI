from __future__ import annotations
import logging
from uuid import UUID
from app.core.supabase import get_supabase
from app.core.redis import get_redis
from app.core.enum.ap import InvoiceAPStatus, APCodingStatus
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.services.ap.gl_coding_service import GLCodingService
from app.services.ap.approval_bridge import APApprovalBridge
from app.workers.base import BaseWorker
logger=logging.getLogger(__name__)
class APCodingWorker(BaseWorker):
    name="ap-coding-worker"
    def __init__(self,db=None): super().__init__(); self.db=db or get_supabase(); self.state=InvoiceStateMachine(self.db); self.service=GLCodingService(self.db); self.approval=APApprovalBridge(self.db)
    async def run(self, *, document_id: UUID):
        redis = await get_redis()
        lock = redis.lock(f"invoiai:ap:coding:{document_id}", timeout=300, blocking=False)
        if not await lock.acquire():
            return
        try:
            return await self._run_once(document_id=document_id)
        finally:
            try:
                await lock.release()
            except Exception:
                logger.warning("Failed to release AP coding lock", exc_info=True)

    async def _run_once(self, *, document_id: UUID):
        doc=self.db.table("documents").select("id,org_id,vendor_id,created_by").eq("id",str(document_id)).single().execute().data
        if not doc or doc.get("ap_status") not in {InvoiceAPStatus.CODING.value,InvoiceAPStatus.CODING_EXCEPTION.value}:
            return
        org = self.db.table("organizations").select("features").eq("id", str(doc["org_id"])).limit(1).execute().data
        features = (org[0].get("features") or {}) if org else {}
        if bool(features.get("personal_mode")):
            return
        lines=self.db.table("document_line_items").select("*").eq("document_id",str(document_id)).order("position").execute().data or []
        if not lines:
            self.db.table("invoice_exceptions").insert({"org_id":doc["org_id"],"document_id":str(document_id),"exception_type":"gl_coding_required","severity":"critical","title":"No invoice line items were extracted","details":{}}).execute()
            await self.state.transition(document_id,UUID(doc["org_id"]),InvoiceAPStatus.CODING_EXCEPTION,triggered_by="worker",reason="No line items to code")
            return
        codings=await self.service.code_document(org_id=UUID(doc["org_id"]),document_id=document_id,line_items=lines,vendor_id=UUID(doc["vendor_id"]) if doc.get("vendor_id") else None)
        needs=any(c.status==APCodingStatus.NEEDS_REVIEW for c in codings)
        self.db.table("documents").update({"gl_coding_status":APCodingStatus.NEEDS_REVIEW.value if needs else APCodingStatus.AUTO_CODED.value}).eq("id",str(document_id)).execute()
        if needs:
            self.db.table("documents").update({"status":"needs_review"}).eq("id",str(document_id)).execute()
            existing=self.db.table("invoice_exceptions").select("id").eq("org_id",doc["org_id"]).eq("document_id",str(document_id)).eq("exception_type","gl_coding_required").eq("status","open").limit(1).execute().data
            if not existing:
                self.db.table("invoice_exceptions").insert({"org_id":doc["org_id"],"document_id":str(document_id),"exception_type":"gl_coding_required","severity":"warning","title":"One or more invoice lines need GL coding review","details":{"coding_count":len(codings)}}).execute()
            await self.state.transition(document_id,UUID(doc["org_id"]),InvoiceAPStatus.CODING_EXCEPTION,triggered_by="worker",reason="One or more lines require coding review")
            return
        # Use analysis ID already attached to the document's latest analysis.
        analysis=self.db.table("document_analyses").select("id").eq("org_id",doc["org_id"]).eq("document_id",str(document_id)).order("created_at",desc=True).limit(1).execute().data
        if not analysis: raise ValueError("Analysis is required before AP approval.")
        await self.state.transition(document_id,UUID(doc["org_id"]),InvoiceAPStatus.AWAITING_APPROVAL,triggered_by="worker")
        await self.approval.create_workflow(org_id=UUID(doc["org_id"]),document_id=document_id,analysis_id=UUID(analysis[0]["id"]),initiated_by=UUID(doc["created_by"]) if doc.get("created_by") else None)
    async def run_pending(self,limit:int=50):
        rows=self.db.table("documents").select("id").in_("ap_status",[InvoiceAPStatus.CODING.value,InvoiceAPStatus.CODING_EXCEPTION.value]).eq("document_type","invoice").limit(limit).execute().data or []
        done=failed=0
        for row in rows:
            try: await self.execute(document_id=UUID(row["id"])); done+=1
            except Exception: failed+=1; logger.exception("AP coding failed for %s",row["id"])
        return {"processed":done,"failed":failed}
