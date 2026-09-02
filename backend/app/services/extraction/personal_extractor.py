from __future__ import annotations
import hashlib,json,logging
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from uuid import UUID
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.enum.finance import IncomeSource,OwnerType,TransactionType
from app.services.finance.expense_service import ExpenseService
from app.services.finance.income_service import IncomeService
from app.core.supabase import get_supabase
log=logging.getLogger(__name__)
client=AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
PROMPT='Extract bank statement data as JSON only: {statement_start,statement_end,opening_balance,closing_balance,transactions:[{date:YYYY-MM-DD,description,amount,type:credit|debit}]}. Never invent missing values.'
class PersonalExtractor:
 def __init__(self,income_service=None,expense_service=None): self.income_service=income_service or IncomeService(); self.expense_service=expense_service or ExpenseService()
 async def extract_statement(self,text):
  if not client:return {"transactions":[],"confidence":0}
  try:
   r=await client.chat.completions.create(model="gpt-4o-mini",temperature=0,response_format={"type":"json_object"},messages=[{"role":"system","content":PROMPT},{"role":"user","content":text[:60000]}],timeout=30); d=json.loads(r.choices[0].message.content or "{}"); d["confidence"]=.85; return d
  except Exception: log.exception("statement extraction failed"); return {"transactions":[],"confidence":0}
 async def process(self,*,owner_type,owner_id,document_id,raw_text,account_id=None):
  d=await self.extract_statement(raw_text); txs=d.get("transactions") or []; db=get_supabase(); imported=skipped=income=expense=0
  for t in txs:
   try: amount=abs(Decimal(str(t.get("amount"))))
   except (InvalidOperation,ValueError,TypeError): skipped+=1; continue
   try: dt=datetime.strptime(str(t.get("date"))[:10],"%Y-%m-%d").date()
   except ValueError: skipped+=1; continue
   desc=str(t.get("description") or "Unknown").strip(); kind=str(t.get("type") or "debit").lower(); typ=TransactionType.INCOME if kind=="credit" else TransactionType.EXPENSE; fp=hashlib.sha256(f"{owner_type.value}:{owner_id}:{dt}:{amount}:{desc.lower()}:{typ.value}".encode()).hexdigest()
   if db.table("financial_transactions").select("id").eq("owner_type",owner_type.value).eq("owner_id",str(owner_id)).eq("transaction_fingerprint",fp).limit(1).execute().data: skipped+=1; continue
   db.table("financial_transactions").insert({"owner_type":owner_type.value,"owner_id":str(owner_id),"account_id":str(account_id) if account_id else None,"transaction_type":typ.value,"amount":str(amount),"currency":"USD","merchant":desc,"description":desc,"transaction_date":dt.isoformat(),"document_id":str(document_id),"transaction_fingerprint":fp,"metadata":{"source":"bank_statement"}}).execute()
   if typ==TransactionType.INCOME: await self.income_service.create(owner_type=owner_type,owner_id=owner_id,amount=amount,source=IncomeSource.OTHER,description=desc,received_date=dt); income+=1
   else: await self.expense_service.create(owner_type=owner_type,owner_id=owner_id,amount=amount,description=desc,expense_date=dt,document_id=document_id); expense+=1
   imported+=1
  db.table("statement_imports").upsert({"owner_type":owner_type.value,"owner_id":str(owner_id),"document_id":str(document_id),"account_id":str(account_id) if account_id else None,"statement_start":d.get("statement_start"),"statement_end":d.get("statement_end"),"opening_balance":d.get("opening_balance"),"closing_balance":d.get("closing_balance"),"transactions_found":len(txs),"transactions_imported":imported,"transactions_skipped":skipped,"confidence":d.get("confidence",0),"status":"completed"},on_conflict="document_id").execute()
  if account_id and d.get("closing_balance") is not None: db.table("financial_accounts").update({"current_balance":d["closing_balance"],"last_synced_at":datetime.now(timezone.utc).isoformat()}).eq("id",str(account_id)).eq("owner_type",owner_type.value).eq("owner_id",str(owner_id)).execute()
  return {"transactions_found":len(txs),"transactions_imported":imported,"transactions_skipped":skipped,"income_recorded":income,"expenses_recorded":expense,"statement_start":d.get("statement_start"),"statement_end":d.get("statement_end"),"closing_balance":d.get("closing_balance"),"confidence":d.get("confidence",0)}
