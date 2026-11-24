from __future__ import annotations
from uuid import UUID
from app.core.enum.ap import InvoiceAPStatus
from app.core.enum.database import IntegrationProvider
from app.core.supabase import get_supabase
from app.integrations.quickbooks.client import QuickBooksClient

from app.core.db import execute

class BillSyncService:
    def __init__(self, db=None): self.db=db or get_supabase()
    async def push_to_quickbooks(self, *, org_id: UUID, document_id: UUID) -> str:
        conn=(await execute(self.db.table("integration_connections").select("id,realm_id,is_active").eq("org_id",str(org_id)).eq("provider",IntegrationProvider.QUICKBOOKS.value).eq("is_active",True).limit(1))).data
        if not conn: raise ValueError("No active QuickBooks connection for this organization.")
        doc=(await execute(self.db.table("documents").select("*, document_line_items(*), invoice_codings(*)").eq("org_id",str(org_id)).eq("id",str(document_id)).single())).data
        vendor=None
        if doc.get("vendor_id"):
            rows=(await execute(self.db.table("vendors").select("*").eq("org_id",str(org_id)).eq("id",str(doc["vendor_id"])).limit(1))).data
            vendor=rows[0] if rows else None
        client=QuickBooksClient(org_id=org_id,realm_id=conn[0]["realm_id"])
        payload=await self._build_payload(doc,vendor)
        result=await client.update_bill(doc["erp_bill_id"],payload) if doc.get("erp_bill_id") else await client.create_bill(payload)
        bill=result.get("Bill") or {}
        bill_id=bill.get("Id")
        if not bill_id: raise RuntimeError("QuickBooks did not return a Bill ID.")
        await execute(self.db.table("documents").update({"erp_bill_id":bill_id,"erp_synced_at":"now()","ap_status":InvoiceAPStatus.PAYMENT_READY.value,"payment_ready_at":"now()"}).eq("org_id",str(org_id)).eq("id",str(document_id)))
        return bill_id
    async def _build_payload(self,doc,vendor):
        lines=[]; codings=doc.get("invoice_codings") or []
        line_items = doc.get("document_line_items") or []
        # Resolve every referenced GL account in one query instead of one query
        # per line item (the previous loop issued N round trips for N lines).
        coded = {}
        for item in line_items:
            coding=next((c for c in codings if str(c.get("line_item_id"))==str(item.get("id"))),None)
            if not coding or not coding.get("gl_account_id"): raise ValueError(f"Line item {item.get('id')} has no approved GL coding.")
            coded[str(item.get("id"))] = str(coding["gl_account_id"])
        accounts_by_id: dict[str, dict] = {}
        if coded:
            account_ids = sorted(set(coded.values()))
            rows=(await execute(self.db.table("chart_of_accounts").select("id,external_id,account_code").in_("id", account_ids))).data or []
            accounts_by_id = {str(row["id"]): row for row in rows}
        for item in line_items:
            account = accounts_by_id.get(coded[str(item.get("id"))])
            if not account or not account.get("external_id"): raise ValueError("GL account is not linked to a QuickBooks external account ID.")
            lines.append({"Amount":float(item.get("amount") or 0),"DetailType":"AccountBasedExpenseLineDetail","AccountBasedExpenseLineDetail":{"AccountRef":{"value":account["external_id"]},"BillableStatus":"NotBillable"},"Description":item.get("description") or ""})
        external_vendor=(vendor or {}).get("external_ids") or {}
        vendor_id=external_vendor.get("quickbooks") or external_vendor.get("QuickBooks")
        if not vendor_id: raise ValueError("Vendor is not linked to a QuickBooks vendor ID.")
        return {"VendorRef":{"value":vendor_id},"TxnDate":str(doc.get("document_date") or ""),"DueDate":str(doc.get("due_date") or ""),"Line":lines,"CurrencyRef":{"value":doc.get("currency") or "USD"},"DocNumber":doc.get("document_number")}
