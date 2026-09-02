from __future__ import annotations
import json, logging
from typing import Any
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.enum.database import DocumentType
log=logging.getLogger(__name__)
PROMPT="Classify this document. Return JSON only: {document_type,confidence,reason}. document_type must be one of invoice,receipt,purchase_order,quotation,contract,bank_statement,credit_note,debit_note,expense_report,delivery_note,payslip,tax_document,audit_report,financial_statement,csv_export,spreadsheet,unknown. Never invent."
KEYWORDS={DocumentType.INVOICE:("invoice","amount due","invoice number"),DocumentType.RECEIPT:("receipt","total paid","cashier"),DocumentType.PURCHASE_ORDER:("purchase order","po number"),DocumentType.BANK_STATEMENT:("bank statement","account statement","opening balance","closing balance","transaction date"),DocumentType.QUOTATION:("quotation","quote","estimate"),DocumentType.CONTRACT:("agreement","contract","terms and conditions"),DocumentType.CREDIT_NOTE:("credit note","credit memo"),DocumentType.DEBIT_NOTE:("debit note","debit memo"),DocumentType.DELIVERY_NOTE:("delivery note","goods received"),DocumentType.EXPENSE_REPORT:("expense report","expense claim"),DocumentType.PAYSLIP:("payslip","net pay","gross pay"),DocumentType.TAX_DOCUMENT:("tax return","tax certificate"),DocumentType.FINANCIAL_STATEMENT:("balance sheet","income statement","cash flow statement")}
class DocumentClassifierService:
 def __init__(self): self.client=AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
 async def classify(self,text:str,filename:str="") -> dict[str,Any]:
  text=(text or "")[:30000]
  if self.client and text:
   try:
    r=await self.client.chat.completions.create(model="gpt-4o-mini",temperature=0,response_format={"type":"json_object"},messages=[{"role":"system","content":PROMPT},{"role":"user","content":f"Filename: {filename}\n{text}"}],timeout=20)
    d=json.loads(r.choices[0].message.content or "{}")
    return {"document_type":DocumentType(str(d.get("document_type","unknown"))).value,"confidence":max(0,min(1,float(d.get("confidence",0)))) ,"reason":str(d.get("reason","AI classification"))[:500],"source":"ai"}
   except Exception: log.exception("classifier fallback")
  h=f"{filename} {text}".lower(); scores={k:sum(x in h for x in v) for k,v in KEYWORDS.items()}; dtype,score=max(scores.items(),key=lambda x:x[1])
  if score==0:return {"document_type":"unknown","confidence":.2,"reason":"No reliable document signals detected.","source":"rules"}
  return {"document_type":dtype.value,"confidence":min(.95,.55+.08*score),"reason":f"Matched {score} document signal(s).","source":"rules"}
