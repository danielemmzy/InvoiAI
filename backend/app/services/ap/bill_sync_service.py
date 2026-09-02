from __future__ import annotations
from uuid import UUID
from app.core.enum.ap import InvoiceAPStatus
from app.core.enum.database import IntegrationProvider
from app.core.supabase import get_supabase
from app.integrations.quickbooks.client import QuickBooksClient

class BillSyncService:
    def __init__(self, db=None): self.db=db or get_supabase()
    async def push_to_quickbooks(self, *, org_id: UUID, document_id: UUID) -> str:
        conn=self.db.table("integration_connections").select("id,realm_id,is_active").eq("org_id",str(org_id)).eq("provider",IntegrationProvider.QUICKBOOKS.value).eq("is_active",True).limit(1).execute().data
        if not conn: raise ValueError("No active QuickBooks connection for this organization.")
        doc=self.db.table("documents").select("*, document_line_items(*), invoice_codings(*)").eq("org_id",str(org_id)).eq("id",str(document_id)).single().execute().data
        vendor=None
        if doc.get("vendor_id"):
            rows=self.db.table("vendors").select("*").eq("org_id",str(org_id)).eq("id",str(doc["vendor_id"])).limit(1).execute().data
            vendor=rows[0] if rows else None
        client=QuickBooksClient(org_id=org_id,realm_id=conn[0]["realm_id"])
        payload=self._build_payload(doc,vendor)
        result=await client.update_bill(doc["erp_bill_id"],payload) if doc.get("erp_bill_id") else await client.create_bill(payload)
        bill=result.get("Bill") or {}
        bill_id=bill.get("Id")
        if not bill_id: raise RuntimeError("QuickBooks did not return a Bill ID.")
        self.db.table("documents").update({"erp_bill_id":bill_id,"erp_synced_at":"now()","ap_status":InvoiceAPStatus.PAYMENT_READY.value,"payment_ready_at":"now()"}).eq("org_id",str(org_id)).eq("id",str(document_id)).execute()
        return bill_id
    def _build_payload(self,doc,vendor):
        lines=[]; codings=doc.get("invoice_codings") or []
        for item in doc.get("document_line_items") or []:
            coding=next((c for c in codings if str(c.get("line_item_id"))==str(item.get("id"))),None)
            if not coding or not coding.get("gl_account_id"): raise ValueError(f"Line item {item.get('id')} has no approved GL coding.")
            account=self.db.table("chart_of_accounts").select("external_id,account_code").eq("id",str(coding["gl_account_id"])).limit(1).execute().data
            if not account or not account[0].get("external_id"): raise ValueError("GL account is not linked to a QuickBooks external account ID.")
            lines.append({"Amount":float(item.get("amount") or 0),"DetailType":"AccountBasedExpenseLineDetail","AccountBasedExpenseLineDetail":{"AccountRef":{"value":account[0]["external_id"]},"BillableStatus":"NotBillable"},"Description":item.get("description") or ""})
        external_vendor=(vendor or {}).get("external_ids") or {}
        vendor_id=external_vendor.get("quickbooks") or external_vendor.get("QuickBooks")
        if not vendor_id: raise ValueError("Vendor is not linked to a QuickBooks vendor ID.")
        return {"VendorRef":{"value":vendor_id},"TxnDate":str(doc.get("document_date") or ""),"DueDate":str(doc.get("due_date") or ""),"Line":lines,"CurrencyRef":{"value":doc.get("currency") or "USD"},"DocNumber":doc.get("document_number")}
