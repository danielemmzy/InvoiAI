from __future__ import annotations
import asyncio
from datetime import date, datetime, UTC
from decimal import Decimal, InvalidOperation
from uuid import UUID
from app.core.supabase import get_supabase

ACTIVE = {"open", "partially_applied"}

from app.core.db import execute

class VendorCreditService:
    """Tenant-scoped vendor credit notes and bill allocations."""
    def __init__(self, db=None): self.db = db or get_supabase()

    async def _vendor(self, org_id: UUID, vendor_id: UUID):
        rows = (await execute(self.db.table("vendors").select("id,name").eq("org_id", str(org_id)).eq("id", str(vendor_id)).limit(1))).data or []
        if not rows: raise ValueError("Vendor not found.")
        return rows[0]

    async def _credit(self, org_id: UUID, credit_id: UUID):
        rows = (await execute(self.db.table("vendor_credits").select("*").eq("org_id", str(org_id)).eq("id", str(credit_id)).limit(1))).data or []
        if not rows: raise ValueError("Vendor credit not found.")
        return rows[0]

    async def _event(self, org_id, credit_id, actor_id, event_type, details=None):
        await execute(self.db.table("vendor_credit_events").insert({"org_id":str(org_id),"vendor_credit_id":str(credit_id),"actor_id":str(actor_id) if actor_id else None,"event_type":event_type,"details":details or {}}))

    async def list_for_vendor(self, org_id: UUID, vendor_id: UUID):
        await self._vendor(org_id, vendor_id)
        credits = (await execute(self.db.table("vendor_credits").select("*").eq("org_id",str(org_id)).eq("vendor_id",str(vendor_id)).order("created_at",desc=True))).data or []
        if not credits:
            return credits

        today = date.today()
        expired = [
            c for c in credits
            if c.get("expires_at")
            and date.fromisoformat(str(c["expires_at"])[:10]) < today
            and c.get("status") in ACTIVE
        ]
        if expired:
            # One statement expires the whole page instead of one per credit.
            await execute(self.db.table("vendor_credits").update({
                "status": "expired", "updated_at": datetime.now(UTC).isoformat()
            }).eq("org_id", str(org_id)).in_(
                "id", [str(c["id"]) for c in expired]
            ).in_("status", list(ACTIVE)))
            for c in expired:
                c["status"] = "expired"

        credit_ids = [str(c["id"]) for c in credits]
        # Applications and events were previously fetched twice per credit.
        applications_response, events_response = await asyncio.gather(
            execute(
                self.db.table("vendor_credit_applications")
                .select("id,vendor_credit_id,document_id,amount,currency,created_at,applied_by")
                .eq("org_id", str(org_id))
                .in_("vendor_credit_id", credit_ids)
                .order("created_at", desc=True)
            ),
            execute(
                self.db.table("vendor_credit_events")
                .select("id,vendor_credit_id,actor_id,event_type,details,created_at")
                .eq("org_id", str(org_id))
                .in_("vendor_credit_id", credit_ids)
                .order("created_at", desc=True)
            ),
        )
        applications_by_credit: dict[str, list] = {}
        for row in applications_response.data or []:
            applications_by_credit.setdefault(str(row.get("vendor_credit_id")), []).append(row)
        events_by_credit: dict[str, list] = {}
        for row in events_response.data or []:
            events_by_credit.setdefault(str(row.get("vendor_credit_id")), []).append(row)

        for c in credits:
            c["applications"] = applications_by_credit.get(str(c["id"]), [])
            c["events"] = events_by_credit.get(str(c["id"]), [])
        return credits

    async def create(self, org_id: UUID, vendor_id: UUID, actor_id: UUID, payload: dict):
        await self._vendor(org_id, vendor_id)
        try: amount = Decimal(str(payload["amount"]))
        except (KeyError, InvalidOperation): raise ValueError("Enter a valid credit amount.")
        if not amount.is_finite() or amount <= 0: raise ValueError("Credit amount must be greater than zero.")
        currency = str(payload.get("currency") or "USD").upper()
        if len(currency) != 3 or not currency.isalpha(): raise ValueError("Currency must be a three-letter ISO code.")
        expires = payload.get("expires_at")
        issued = date.fromisoformat(str(payload.get("issued_at") or date.today())[:10])
        if expires and date.fromisoformat(str(expires)[:10]) < max(date.today(), issued): raise ValueError("Expiry date cannot be in the past or before the issue date.")
        row = {"org_id":str(org_id),"vendor_id":str(vendor_id),"credit_number":(payload.get("credit_number") or "").strip() or None,"reason":(payload.get("reason") or "").strip() or None,"amount":str(amount),"remaining_amount":str(amount),"currency":currency,"issued_at":str(payload.get("issued_at") or date.today()),"expires_at":str(expires)[:10] if expires else None,"status":"open","notes":(payload.get("notes") or "").strip() or None,"created_by":str(actor_id)}
        result = (await execute(self.db.table("vendor_credits").insert(row))).data or []
        if not result: raise RuntimeError("Vendor credit could not be created.")
        c=result[0]; await self._event(org_id,c["id"],actor_id,"created",{"amount":str(amount),"currency":currency})
        return c

    async def cancel(self, org_id: UUID, credit_id: UUID, actor_id: UUID, reason: str):
        c=await self._credit(org_id,credit_id)
        if c["status"] not in ACTIVE: raise ValueError("Only open or partially applied credits can be cancelled.")
        if Decimal(str(c["remaining_amount"])) < Decimal(str(c["amount"])): raise ValueError("A credit with applied value cannot be cancelled; reverse its bill applications first.")
        updated=(await execute(self.db.table("vendor_credits").update({"status":"cancelled","cancelled_at":datetime.now(UTC).isoformat(),"cancellation_reason":reason,"updated_at":datetime.now(UTC).isoformat()}).eq("org_id",str(org_id)).eq("id",str(credit_id)).eq("status",c["status"]))).data or []
        if not updated: raise ValueError("Credit changed while being cancelled. Refresh and try again.")
        await self._event(org_id,credit_id,actor_id,"cancelled",{"reason":reason}); return updated[0]

    async def apply(self, org_id: UUID, credit_id: UUID, actor_id: UUID, document_id: UUID, amount: Decimal):
        c=await self._credit(org_id,credit_id)
        if c["status"] not in ACTIVE: raise ValueError("This credit is not available for application.")
        if c.get("expires_at") and date.fromisoformat(str(c["expires_at"])[:10]) < date.today():
            (await execute(self.db.table("vendor_credits").update({"status":"expired","updated_at":datetime.now(UTC).isoformat()}).eq("org_id",str(org_id)).eq("id",str(credit_id)))); raise ValueError("This credit has expired.")
        if not amount.is_finite() or amount <= 0: raise ValueError("Application amount must be greater than zero.")
        if amount > Decimal(str(c["remaining_amount"])): raise ValueError("Application exceeds the available credit balance.")
        docs=(await execute(self.db.table("documents").select("id,vendor_id,currency,total_amount,amount_due,ap_status").eq("org_id",str(org_id)).eq("id",str(document_id)).limit(1))).data or []
        if not docs: raise ValueError("Bill not found in this organization.")
        d=docs[0]
        if str(d.get("vendor_id")) != str(c["vendor_id"]): raise ValueError("Credit can only be applied to a bill from the same vendor.")
        if str(d.get("currency") or "USD").upper() != str(c["currency"]).upper(): raise ValueError("Bill and credit currencies must match.")
        if str(d.get("ap_status") or "").lower() in {"paid","void","cancelled","rejected"}: raise ValueError("Credit cannot be applied to a paid or inactive bill.")
        already=(await execute(self.db.table("vendor_credit_applications").select("amount").eq("org_id",str(org_id)).eq("document_id",str(document_id)))).data or []
        applied=sum((Decimal(str(x["amount"])) for x in already),Decimal("0"))
        balance = Decimal(str(d.get("amount_due"))) if d.get("amount_due") is not None else max(Decimal(str(d.get("total_amount") or 0)) - applied, Decimal("0"))
        if amount > max(balance,Decimal("0")): raise ValueError("Application exceeds the bill's remaining balance.")
        now=datetime.now(UTC).isoformat(); remaining=Decimal(str(c["remaining_amount"]))-amount
        new_status="applied" if remaining == 0 else "partially_applied"
        # Conditional balance update prevents two concurrent requests from consuming the same balance.
        updated=(await execute(self.db.table("vendor_credits").update({"remaining_amount":str(remaining),"status":new_status,"updated_at":now}).eq("org_id",str(org_id)).eq("id",str(credit_id)).eq("remaining_amount",str(c["remaining_amount"])))).data or []
        if not updated: raise ValueError("Credit balance changed concurrently. Refresh and try again.")
        try:
            app=(await execute(self.db.table("vendor_credit_applications").insert({"org_id":str(org_id),"vendor_credit_id":str(credit_id),"vendor_id":str(c["vendor_id"]),"document_id":str(document_id),"amount":str(amount),"currency":c["currency"],"applied_by":str(actor_id)}))).data or []
            if not app: raise RuntimeError("Credit application could not be saved.")
            new_bill_balance = max(balance - amount, Decimal("0"))
            bill_update = {"amount_due": str(new_bill_balance), "updated_at": now}
            if new_bill_balance == 0:
                bill_update["ap_status"] = "credited"
                bill_update["payment_status"] = "credited"
            elif new_bill_balance < Decimal(str(d.get("total_amount") or 0)):
                bill_update["ap_status"] = "partially_paid"
            await execute(self.db.table("documents").update(bill_update).eq("org_id",str(org_id)).eq("id",str(document_id)))
        except Exception:
            # Best-effort compensation if allocation or bill update fails.
            await execute(self.db.table("vendor_credits").update({"remaining_amount":str(c["remaining_amount"]),"status":c["status"],"updated_at":datetime.now(UTC).isoformat()}).eq("org_id",str(org_id)).eq("id",str(credit_id)).eq("remaining_amount",str(remaining)))
            await execute(self.db.table("vendor_credit_applications").delete().eq("org_id",str(org_id)).eq("vendor_credit_id",str(credit_id)).eq("document_id",str(document_id)).eq("amount",str(amount)))
            raise
        await self._event(org_id,credit_id,actor_id,"applied_to_bill",{"document_id":str(document_id),"amount":str(amount),"currency":c["currency"]})
        return app[0]

    async def events(self, org_id: UUID, credit_id: UUID):
        await self._credit(org_id,credit_id)
        return (await execute(self.db.table("vendor_credit_events").select("*").eq("org_id",str(org_id)).eq("vendor_credit_id",str(credit_id)).order("created_at",desc=True))).data or []
