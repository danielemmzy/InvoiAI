from __future__ import annotations
from datetime import UTC, datetime
from uuid import UUID
from app.core.enum.ap import InvoiceAPStatus
from app.core.supabase import get_supabase

TRANSITIONS = {
    InvoiceAPStatus.RECEIVED: {InvoiceAPStatus.EXTRACTING, InvoiceAPStatus.VALIDATING, InvoiceAPStatus.REJECTED, InvoiceAPStatus.ON_HOLD},
    InvoiceAPStatus.EXTRACTING: {InvoiceAPStatus.VALIDATING, InvoiceAPStatus.REJECTED},
    InvoiceAPStatus.VALIDATING: {InvoiceAPStatus.MATCHING, InvoiceAPStatus.CODING, InvoiceAPStatus.MATCH_EXCEPTION, InvoiceAPStatus.REJECTED},
    InvoiceAPStatus.MATCHING: {InvoiceAPStatus.CODING, InvoiceAPStatus.MATCH_EXCEPTION, InvoiceAPStatus.ON_HOLD},
    InvoiceAPStatus.MATCH_EXCEPTION: {InvoiceAPStatus.CODING, InvoiceAPStatus.REJECTED, InvoiceAPStatus.ON_HOLD},
    InvoiceAPStatus.CODING: {InvoiceAPStatus.AWAITING_APPROVAL, InvoiceAPStatus.CODING_EXCEPTION, InvoiceAPStatus.REJECTED},
    InvoiceAPStatus.CODING_EXCEPTION: {InvoiceAPStatus.AWAITING_APPROVAL, InvoiceAPStatus.REJECTED, InvoiceAPStatus.CODING},
    InvoiceAPStatus.AWAITING_APPROVAL: {InvoiceAPStatus.APPROVED, InvoiceAPStatus.REJECTED, InvoiceAPStatus.ON_HOLD},
    InvoiceAPStatus.APPROVED: {InvoiceAPStatus.SYNCING_TO_ERP, InvoiceAPStatus.PAYMENT_READY},
    InvoiceAPStatus.SYNCING_TO_ERP: {InvoiceAPStatus.PAYMENT_READY, InvoiceAPStatus.APPROVED},
    InvoiceAPStatus.PAYMENT_READY: {InvoiceAPStatus.PAID},
    InvoiceAPStatus.PAID: {InvoiceAPStatus.RECONCILED},
    InvoiceAPStatus.ON_HOLD: {InvoiceAPStatus.MATCHING, InvoiceAPStatus.CODING, InvoiceAPStatus.AWAITING_APPROVAL, InvoiceAPStatus.REJECTED},
    InvoiceAPStatus.REJECTED: set(),
    InvoiceAPStatus.RECONCILED: set(),
}

class InvoiceStateMachine:
    def __init__(self, db=None): self.db = db or get_supabase()
    async def get_status(self, document_id: UUID) -> InvoiceAPStatus:
        row=self.db.table("documents").select("ap_status").eq("id",str(document_id)).single().execute().data
        return InvoiceAPStatus(row.get("ap_status") or InvoiceAPStatus.RECEIVED.value)
    def can_transition(self, from_status, to_status):
        return to_status in TRANSITIONS.get(InvoiceAPStatus(from_status), set())
    async def transition(self, document_id: UUID, org_id: UUID, to_status: InvoiceAPStatus, *, actor_id: UUID|None=None, triggered_by="system", reason=None, metadata=None):
        current=await self.get_status(document_id)
        if current == to_status: return current
        if not self.can_transition(current,to_status):
            raise ValueError(f"Invalid AP transition: {current.value} -> {to_status.value}")
        self.db.table("documents").update({"ap_status":to_status.value,"updated_at":datetime.now(UTC).isoformat()}).eq("id",str(document_id)).eq("org_id",str(org_id)).execute()
        self.db.table("invoice_status_log").insert({"org_id":str(org_id),"document_id":str(document_id),"from_status":current.value,"to_status":to_status.value,"triggered_by":triggered_by,"actor_id":str(actor_id) if actor_id else None,"reason":reason,"metadata":metadata or {}}).execute()
        return to_status
