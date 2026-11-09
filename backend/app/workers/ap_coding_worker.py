from __future__ import annotations

import logging
from uuid import UUID

from app.core.supabase import get_supabase
from app.core.redis import get_redis
from app.core.enum.ap import InvoiceAPStatus, APCodingStatus
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.services.ap.gl_coding_service import GLCodingService
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class APCodingWorker(BaseWorker):
    name = "ap-coding-worker"

    def __init__(self, db=None):
        super().__init__()
        self.db = db or get_supabase()
        self.state = InvoiceStateMachine(self.db)
        self.service = GLCodingService(self.db)

    async def run(self, *, document_id: UUID):
        redis = await get_redis()
        lock = redis.lock(f"invoiai:ap:coding:{document_id}", timeout=300, blocking=False)
        if not await lock.acquire():
            logger.info("AP coding already running for %s", document_id)
            return
        try:
            return await self._run_once(document_id=document_id)
        finally:
            try: await lock.release()
            except Exception: logger.warning("Failed to release AP coding lock", exc_info=True)

    async def _run_once(self, *, document_id: UUID):
        doc = self.db.table("documents").select("id,org_id,vendor_id,created_by,ap_enabled,ap_status").eq("id", str(document_id)).single().execute().data
        if not doc or not bool(doc.get("ap_enabled")): return
        if doc.get("ap_status") not in {InvoiceAPStatus.CODING.value, InvoiceAPStatus.CODING_EXCEPTION.value}: return
        org = self.db.table("organizations").select("features").eq("id", str(doc["org_id"])).limit(1).execute().data
        features = (org[0].get("features") or {}) if org else {}
        if bool(features.get("personal_mode")): return
        lines = self.db.table("document_line_items").select("*").eq("org_id", str(doc["org_id"])).eq("document_id", str(document_id)).order("position").execute().data or []
        if not lines:
            existing = self.db.table("invoice_exceptions").select("id").eq("org_id", doc["org_id"]).eq("document_id", str(document_id)).eq("exception_type", "gl_coding_required").in_("status", ["open", "in_review", "escalated"]).limit(1).execute().data
            if not existing:
                self.db.table("invoice_exceptions").insert({"org_id": doc["org_id"], "document_id": str(document_id), "exception_type": "gl_coding_required", "severity": "critical", "title": "No invoice line items were extracted", "details": {}}).execute()
            self.db.table("documents").update({"processing_step": "ap_coding_exception", "processing_message": "No invoice line items were extracted. Review the invoice before continuing.", "processing_progress": 85, "gl_coding_status": "needs_review"}).eq("id", str(document_id)).execute()
            await self.state.transition(document_id, UUID(doc["org_id"]), InvoiceAPStatus.CODING_EXCEPTION, triggered_by="worker", reason="No line items to code")
            return

        total = len(lines)
        self.db.table("documents").update({"processing_step": "ap_coding", "processing_message": f"Assigning GL accounts to {total} invoice line item(s)…", "processing_progress": 70, "error_message": None}).eq("id", str(document_id)).execute()

        async def update_progress(done: int, count: int):
            progress = 70 + int(18 * done / max(count, 1))
            self.db.table("documents").update({"processing_step": "ap_coding", "processing_message": f"Assigning GL accounts: {done} of {count} line item(s) checked", "processing_progress": progress}).eq("id", str(document_id)).execute()

        codings = await self.service.code_document(org_id=UUID(doc["org_id"]), document_id=document_id, line_items=lines, vendor_id=UUID(doc["vendor_id"]) if doc.get("vendor_id") else None, on_progress=update_progress)
        needs = any(c.status == APCodingStatus.NEEDS_REVIEW for c in codings)
        self.db.table("documents").update({"gl_coding_status": APCodingStatus.NEEDS_REVIEW.value if needs else APCodingStatus.AUTO_CODED.value}).eq("id", str(document_id)).eq("org_id", str(doc["org_id"])).execute()
        if needs:
            self.db.table("documents").update({"status": "needs_review", "processing_step": "ap_coding_exception", "processing_message": "GL suggestions are ready, but one or more lines need a human account assignment.", "processing_progress": 85}).eq("id", str(document_id)).execute()
            existing = self.db.table("invoice_exceptions").select("id").eq("org_id", doc["org_id"]).eq("document_id", str(document_id)).eq("exception_type", "gl_coding_required").in_("status", ["open", "in_review", "escalated"]).limit(1).execute().data
            if not existing:
                self.db.table("invoice_exceptions").insert({"org_id": doc["org_id"], "document_id": str(document_id), "exception_type": "gl_coding_required", "severity": "warning", "title": "One or more invoice lines need GL coding review", "details": {"coding_count": len(codings)}}).execute()
            await self.state.transition(document_id, UUID(doc["org_id"]), InvoiceAPStatus.CODING_EXCEPTION, triggered_by="worker", reason="One or more lines require coding review")
            return

        # A successful retry must leave the exception state; otherwise the UI keeps
        # showing 85% and asks the reviewer to resolve the same issue again.
        current = await self.state.get_status(document_id)
        if current == InvoiceAPStatus.CODING_EXCEPTION:
            await self.state.transition(document_id, UUID(doc["org_id"]), InvoiceAPStatus.CODING, triggered_by="worker", reason="GL coding completed after exception correction")
        self.db.table("documents").update({"status": "needs_review", "processing_step": "ap_ready_to_submit", "processing_message": "Matching and GL coding are complete. Ready to submit for approval.", "processing_progress": 90, "error_message": None}).eq("id", str(document_id)).eq("org_id", str(doc["org_id"])).execute()

    async def run_pending(self, limit: int = 50):
        rows = self.db.table("documents").select("id").eq("ap_enabled", True).in_("ap_status", [InvoiceAPStatus.CODING.value, InvoiceAPStatus.CODING_EXCEPTION.value]).eq("document_type", "invoice").limit(limit).execute().data or []
        done = failed = 0
        for row in rows:
            try: await self.execute(document_id=UUID(row["id"])); done += 1
            except Exception: failed += 1; logger.exception("AP coding failed for %s", row["id"])
        return {"processed": done, "failed": failed}
