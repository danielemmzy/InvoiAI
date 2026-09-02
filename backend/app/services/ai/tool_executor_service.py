"""
============================================================
Tool Executor

Responsible for executing AI tools.

Copilot decides WHAT tool to call.
ToolExecutor performs the work.

No OpenAI logic here (except generate_followup_email, which
IS an LLM-drafting tool by definition — it never computes
numbers, only writes prose from facts already fetched).

Extended (Flow 7/8/14) to dispatch:
- get_vendor_price_changes  -> VendorAnalyzer (pure Python math)
- find_similar_vendors      -> SearchService.search_vendors (pgvector)
- generate_followup_email   -> OpenAI drafts text from real facts
- record_paycheck           -> IncomeService (Personal Mode)
- log_expense                -> ExpenseService (Personal Mode)

org_id/user_id are now threaded through from CopilotService so
these org-scoped tools have the context they need — the
original 3 tools (find_document/find_vendor/archive_document)
don't need them and remain unchanged.
============================================================
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.core.enum.finance import IncomeSource, OwnerType
from app.repositories.document.document_repository import DocumentRepository
from app.repositories.document.vendor_repository import VendorRepository
from app.repositories.organization.organization_repository import OrganizationRepository
from app.services.finance.income_service import IncomeService
from app.services.finance.expense_service import ExpenseService
from app.services.finance.planning_service import PlanningService
from app.services.search_service import SearchService
from app.services.insights.analyzers.vendor_analyzer import VendorAnalyzer


class ToolExecutor:

    def __init__(
        self,
        *,
        document_repository: DocumentRepository | None = None,
        vendor_repository: VendorRepository | None = None,
        organization_repository: OrganizationRepository | None = None,
        search_service: SearchService | None = None,
        income_service: IncomeService | None = None,
        expense_service: ExpenseService | None = None,
        planning_service: PlanningService | None = None,
        vendor_analyzer: VendorAnalyzer | None = None,
    ):
        self.documents = document_repository or DocumentRepository()
        self.vendors = vendor_repository or VendorRepository()
        self.organizations = organization_repository or OrganizationRepository()
        self.search_service = search_service or SearchService()
        self.income_service = income_service or IncomeService()
        self.expense_service = expense_service or ExpenseService()
        self.planning_service = planning_service or PlanningService()
        self.vendor_analyzer = vendor_analyzer or VendorAnalyzer(self.vendors, self.documents)

    async def execute(
        self,
        *,
        tool_name: str,
        arguments: dict,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ):

        if tool_name == "find_document":
            return await self.find_document(
                **arguments,
            )

        if tool_name == "find_vendor":
            return await self.find_vendor(
                **arguments,
            )

        if tool_name == "archive_document":
            return await self.archive_document(
                **arguments,
            )

        if tool_name == "get_document_workflow":
            return await self.get_document_workflow(org_id=org_id, **arguments)

        if tool_name == "get_finance_snapshot":
            return await self.get_finance_snapshot(user_id=user_id)

        if tool_name == "get_vendor_price_changes":
            return await self.get_vendor_price_changes(org_id=org_id)

        if tool_name == "find_similar_vendors":
            return await self.find_similar_vendors(org_id=org_id, **arguments)

        if tool_name == "generate_followup_email":
            return await self.generate_followup_email(
                org_id=org_id, **arguments
            )

        if tool_name == "record_paycheck":
            return await self.record_paycheck(
                org_id=org_id, user_id=user_id, **arguments
            )

        if tool_name == "log_expense":
            return await self.log_expense(
                org_id=org_id, user_id=user_id, **arguments
            )

        raise ValueError(f"Unknown tool: {tool_name}")

    async def find_document(
        self,
        *,
        document_id: UUID,
    ):

        return await self.documents.get_document(
            document_id,
        )

    async def find_vendor(
        self,
        *,
        vendor_id: UUID,
    ):

        return await self.vendors.get(
            vendor_id,
        )

    async def archive_document(
        self,
        *,
        document_id: UUID,
        archived_by: UUID,
        reason: str | None = None,
    ):

        return await self.documents.archive_document(
            document_id,
            archived_by,
            reason,
        )

    async def get_document_workflow(self, *, org_id: UUID|None, document_id: str):
        if org_id is None:return {"error":"org_id is required"}
        return self.documents.table().select("id,document_type,workflow_route,classification_confidence,classification_reason,status,pipeline_stage,ap_status,match_status,gl_coding_status").eq("id",document_id).eq("org_id",str(org_id)).single().execute().data or {"error":"document not found"}

    async def get_finance_snapshot(self, *, user_id: UUID|None):
        if user_id is None:return {"error":"user_id is required"}
        from app.core.supabase import get_supabase
        db=get_supabase(); ot=OwnerType.PERSONAL.value; oid=str(user_id)
        accounts=db.table("financial_accounts").select("name,current_balance,currency,last_synced_at").eq("owner_type",ot).eq("owner_id",oid).eq("is_active",True).execute().data or []
        latest=db.table("statement_imports").select("created_at,statement_end,transactions_imported").eq("owner_type",ot).eq("owner_id",oid).order("created_at",desc=True).limit(1).execute().data or []
        return {"accounts":accounts,"latest_statement":latest[0] if latest else None,"mode":"personal"}

    # =========================================================
    # Business tools (Flow 7 / Flow 10 / Flow 14)
    # =========================================================

    async def get_vendor_price_changes(self, *, org_id: UUID | None):
        """
        Flow 7's example query: "Which vendor increased prices
        most this month?" Reuses the Insight Engine's
        VendorAnalyzer directly — one source of truth for the
        math, whether it's the dashboard or the copilot asking.
        """
        if org_id is None:
            return {"error": "org_id is required"}

        result = await self.vendor_analyzer.run(org_id)
        return result.data

    async def find_similar_vendors(
        self,
        *,
        org_id: UUID | None,
        query: str,
        limit: int = 5,
    ):
        """Flow 14 — semantic vendor search via pgvector."""
        if org_id is None:
            return {"error": "org_id is required"}

        return await self.search_service.search_vendors(
            org_id=org_id, query=query, limit=limit
        )

    async def generate_followup_email(
        self,
        *,
        org_id: UUID | None,
        customer_id: str | None = None,
        document_id: str | None = None,
    ):
        """
        Flow 10's "Copilot tool called: generate_followup_email
        (customer_id)" — drafts an overdue-payment reminder from
        the actual document facts, not invented ones.
        """
        if not document_id:
            return {"error": "document_id is required"}

        document = await self.documents.get_document(UUID(document_id))
        if document is None:
            return {"error": "document not found"}

        from openai import AsyncOpenAI

        from app.core.config import settings

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        prompt = (
            f"Write a brief, polite payment reminder email. "
            f"Invoice number: {document.document_number}. "
            f"Amount: {document.total_amount} {document.currency}. "
            f"Due date: {document.due_date}. "
            f"Vendor/biller: {document.vendor_name}. "
            f"Keep it under 120 words."
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "email_draft": response.choices[0].message.content,
            "document_id": document_id,
        }

    # =========================================================
    # Personal tools (Flow 8)
    # =========================================================

    async def record_paycheck(
        self,
        *,
        org_id: UUID | None,
        user_id: UUID | None,
        amount: float,
        source: str = "salary",
    ):
        if user_id is None:
            return {"error": "user_id is required"}

        owner_type, owner_id = self._resolve_owner(org_id, user_id)

        try:
            resolved_source = IncomeSource(source)
        except ValueError:
            resolved_source = IncomeSource.OTHER

        income = await self.income_service.create(
            owner_type=owner_type,
            owner_id=owner_id,
            amount=Decimal(str(amount)),
            source=resolved_source,
        )

        plan = await self.planning_service.generate_plan(
            owner_type, owner_id, Decimal(str(amount))
        )

        return {
            "income_id": str(income.id),
            "amount": amount,
            "plan": plan.plan,
            "advice": plan.advice,
        }

    async def log_expense(
        self,
        *,
        org_id: UUID | None,
        user_id: UUID | None,
        amount: float,
        description: str,
    ):
        if user_id is None:
            return {"error": "user_id is required"}

        owner_type, owner_id = self._resolve_owner(org_id, user_id)

        expense = await self.expense_service.create(
            owner_type=owner_type,
            owner_id=owner_id,
            amount=Decimal(str(amount)),
            description=description,
        )

        return {
            "expense_id": str(expense.id),
            "amount": amount,
            "category": expense.category.value
            if hasattr(expense.category, "value")
            else expense.category,
        }

    @staticmethod
    def _resolve_owner(org_id: UUID | None, user_id: UUID) -> tuple:
        """
        Personal-mode tools always own by user, matching Flow 8's
        "ctx.org.features.personal_mode = true -> owner_type =
        PERSONAL, owner_id = ctx.user_id" — these tools are only
        ever registered in PERSONAL_TOOLS to begin with (see
        tool_definitions.py), so this is always PERSONAL in
        practice, but org_id is accepted for symmetry with the
        business tools above.
        """
        return OwnerType.PERSONAL, user_id
