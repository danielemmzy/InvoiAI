from uuid import UUID
from app.core.enum.ap import APExceptionStatus, InvoiceAPStatus
from app.core.supabase import get_supabase
from app.repositories.ap.exception_repository import InvoiceExceptionRepository
from app.services.ap.invoice_state_machine import InvoiceStateMachine
class ExceptionService:
    def __init__(self): self.repo=InvoiceExceptionRepository(); self.db=get_supabase(); self.state=InvoiceStateMachine(self.db)
    async def list_open(self,org_id): return await self.repo.list_open(org_id)
    async def list_for_document(self,org_id,document_id): return await self.repo.list_by_document(org_id,document_id)
    async def resolve(self,org_id,exception_id,user_id,note,waive=False):
        status=APExceptionStatus.WAIVED.value if waive else APExceptionStatus.RESOLVED.value
        result=await self.repo.resolve(org_id,exception_id,user_id,note,status)
        row=self.db.table("invoice_exceptions").select("document_id").eq("org_id",str(org_id)).eq("id",str(exception_id)).limit(1).execute().data
        if row:
            document_id=UUID(row[0]["document_id"])
            open_rows=self.db.table("invoice_exceptions").select("id").eq("org_id",str(org_id)).eq("document_id",str(document_id)).in_("status",["open","in_review","escalated"]).execute().data or []
            if not open_rows:
                current=await self.state.get_status(document_id)
                if current==InvoiceAPStatus.MATCH_EXCEPTION:
                    await self.state.transition(document_id,org_id,InvoiceAPStatus.CODING,actor_id=user_id,triggered_by="user",reason="All matching exceptions resolved")
                elif current==InvoiceAPStatus.CODING_EXCEPTION:
                    await self.state.transition(document_id,org_id,InvoiceAPStatus.AWAITING_APPROVAL,actor_id=user_id,triggered_by="user",reason="All coding exceptions resolved")
        return result
