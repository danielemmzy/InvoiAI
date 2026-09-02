from __future__ import annotations
import json, logging
from decimal import Decimal
from uuid import UUID
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.enum.ap import APCodingSource, APCodingStatus
from app.models.domain.ap import InvoiceCoding
from app.repositories.ap.chart_of_accounts_repository import ChartOfAccountRepository
from app.repositories.ap.coding_repository import InvoiceCodingRepository, CodingRuleRepository

logger=logging.getLogger(__name__)
AUTO_CODE_CONFIDENCE=Decimal("80")

class GLCodingService:
    def __init__(self, db=None):
        self.coa=ChartOfAccountRepository(); self.codings=InvoiceCodingRepository(); self.rules=CodingRuleRepository(); self.client=AsyncOpenAI(api_key=settings.openai_api_key)
    async def code_document(self, *, org_id: UUID, document_id: UUID, line_items: list[dict], vendor_id: UUID|None=None):
        rules=await self.rules.list_active(org_id); accounts=await self.coa.list_by_org(org_id); result=[]
        for item in line_items:
            coding=await self._code_line(org_id,document_id,item,vendor_id,rules,accounts)
            result.append(coding); await self.codings.save_coding(coding)
            update={"coding_confidence":float(coding.confidence),"coding_source":coding.source.value}
            if coding.gl_account_id:
                account=next((a for a in accounts if a.id==coding.gl_account_id),None)
                update.update({"gl_account_id":str(coding.gl_account_id),"gl_account_code":account.account_code if account else None,"gl_account_name":account.account_name if account else None})
            if coding.department_id: update["department_id"]=str(coding.department_id)
            if coding.cost_center_id: update["cost_center_id"]=str(coding.cost_center_id)
            if coding.project_id: update["project_id"]=str(coding.project_id)
            if coding.tax_code_id: update["tax_code_id"]=str(coding.tax_code_id)
            self.codings.db.table("document_line_items").update(update).eq("id",str(item["id"])).eq("document_id",str(document_id)).execute()
        return result
    async def _code_line(self,org_id,document_id,item,vendor_id,rules,accounts):
        base=dict(org_id=org_id,document_id=document_id,line_item_id=item.get("id"),amount=item.get("amount"))
        for rule in rules:
            if self._rule_matches(rule,item,vendor_id):
                await self.rules.increment_match_count(rule.id)
                return InvoiceCoding(**base,gl_account_id=rule.gl_account_id,department_id=rule.department_id,cost_center_id=rule.cost_center_id,project_id=rule.project_id,tax_code_id=rule.tax_code_id,confidence=Decimal("95"),source=APCodingSource.RULE,coding_rule_id=rule.id,status=APCodingStatus.AUTO_CODED)
        # Historical coding: use the same vendor's recent line-item coding.
        # This is intentionally deterministic; the LLM is only used after this lookup.
        desc=(item.get("description") or "").strip()
        if vendor_id and desc:
            docs=self.codings.db.table("documents").select("id").eq("org_id",str(org_id)).eq("vendor_id",str(vendor_id)).neq("id",str(document_id)).order("created_at",desc=True).limit(25).execute().data or []
            for old_doc in docs:
                old_items=self.codings.db.table("document_line_items").select("id,description").eq("document_id",old_doc["id"]).ilike("description",f"%{desc[:80]}%").limit(3).execute().data or []
                for old_item in old_items:
                    old_coding=self.codings.db.table("invoice_codings").select("gl_account_id").eq("document_id",old_doc["id"]).eq("line_item_id",old_item["id"]).limit(1).execute().data or []
                    if old_coding and old_coding[0].get("gl_account_id"):
                        account=next((a for a in accounts if str(a.id)==str(old_coding[0]["gl_account_id"])),None)
                        if account:
                            return InvoiceCoding(**base,gl_account_id=account.id,confidence=Decimal("90"),source=APCodingSource.HISTORICAL,status=APCodingStatus.AUTO_CODED)
        if accounts:
            suggestion=await self._ai_suggest(item,accounts)
            if suggestion:
                confidence=Decimal(str(suggestion.get("confidence",60)))
                account=suggestion.get("account")
                return InvoiceCoding(**base,gl_account_id=account.id if account else None,confidence=confidence,source=APCodingSource.AI_SUGGESTED,status=APCodingStatus.AUTO_CODED if confidence>=AUTO_CODE_CONFIDENCE else APCodingStatus.NEEDS_REVIEW)
        return InvoiceCoding(**base,confidence=Decimal("0"),source=APCodingSource.MANUAL,status=APCodingStatus.NEEDS_REVIEW)
    @staticmethod
    def _rule_matches(rule,item,vendor_id):
        if rule.vendor_id and rule.vendor_id!=vendor_id:return False
        if rule.description_pattern and rule.description_pattern.lower() not in (item.get("description") or "").lower():return False
        if rule.sku_pattern and rule.sku_pattern.lower() not in (item.get("sku") or "").lower():return False
        return True
    async def _ai_suggest(self,item,accounts):
        choices=[{"id":str(a.id),"code":a.account_code,"name":a.account_name,"type":a.account_type} for a in accounts if a.is_postable]
        if not choices:return None
        prompt="Select the best existing GL account for this invoice line. Never invent an account. Return JSON: {account_code,confidence,reason}.\nLine: "+json.dumps({k:item.get(k) for k in ("description","amount","category","sku")})+"\nAccounts:\n"+json.dumps(choices[:200])
        try:
            r=await self.client.chat.completions.create(model="gpt-4o-mini",temperature=0,response_format={"type":"json_object"},messages=[{"role":"system","content":"You are an AP accounting assistant. Select only from the supplied chart of accounts."},{"role":"user","content":prompt}])
            data=json.loads(r.choices[0].message.content or "{}")
            account=next((a for a in accounts if a.account_code==data.get("account_code")),None)
            return {"account":account,"confidence":data.get("confidence",60),"reason":data.get("reason") } if account else None
        except Exception:
            logger.exception("GL coding AI suggestion failed")
            return None
