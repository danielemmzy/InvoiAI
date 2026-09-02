"""
============================================================
Finance Router

HTTP entrypoint for Flow 8 (Personal Finance Logging).
Mirrors the shape of the copilot's PERSONAL_TOOLS
(record_paycheck / log_expense) so the same logic is reachable
both from chat and from a future settings/finance dashboard
page without duplicating business rules.

Owner scoping: when the active organization has
feature_flags["personal_mode"] enabled, rows are owned by the
user directly (OwnerType.PERSONAL); otherwise they're owned by
the organization (OwnerType.ORGANIZATION), matching Flow 8's
"ctx.org.features.personal_mode" check.
============================================================
"""

from __future__ import annotations

from datetime import timezone, datetime, date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException, Query, Response

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.enum.finance import OwnerType
from app.core.ocm import get_org_context
from app.mappers.finance_mapper import (
    BudgetCategoryMapper,
    DebtMapper,
    ExpenseMapper,
    GoalMapper,
    IncomeEntryMapper,
    RecurringItemMapper,
)
from app.schemas.finance import (
    BudgetCategoryResponse,
    BudgetSummaryResponse,
    DebtResponse,
    ExpenseCreate,
    ExpenseResponse,
    GoalResponse,
    IncomeCreate,
    IncomeResponse,
    RecurringItemResponse,
)
from app.services.finance.expense_service import ExpenseService
from app.services.finance.income_service import IncomeService
from app.services.finance.planning_service import PlanningService
from app.core.container import get_container
from app.core.authorization import require_permission
from app.core.permissions import VIEW_FINANCE, MANAGE_FINANCE
from app.core.supabase import get_supabase
from app.core.limiter import limiter
from app.core.cache import cache
import asyncio

router = APIRouter(prefix="/finance", tags=["Finance"])


def _owner(
    user: AuthUser,
    ctx: OrganizationContext,
) -> tuple[OwnerType, UUID]:
    if ctx.feature_flags.get("personal_mode", False):
        return OwnerType.PERSONAL, user.id
    return OwnerType.ORGANIZATION, ctx.org_id


# ============================================================
# Income
# ============================================================

@router.post("/income", response_model=IncomeResponse)
@limiter.limit("30/minute")
async def record_income(
    response: Response,
    request: Request,
    payload: IncomeCreate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_FINANCE)),
):
    owner_type, owner_id = _owner(user, ctx)

    income = await get_container().income_service.create(
        owner_type=owner_type,
        owner_id=owner_id,
        amount=payload.amount,
        source=payload.source,
        currency=payload.currency,
        description=payload.description,
        received_date=payload.received_date,
        is_recurring=payload.is_recurring,
    )

    # Regenerate the allocation plan whenever new income lands,
    # matching Flow 8's "planning_service.generate_plan(owner_id)".
    await get_container().planning_service.generate_plan(
        owner_type,
        owner_id,
        payload.amount,
    )

    return IncomeEntryMapper.to_response(income)


@router.get("/income", response_model=list[IncomeResponse])
async def list_income(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    limit: int = 50,
    offset: int = 0,
):
    owner_type, owner_id = _owner(user, ctx)
    entries = await get_container().income_service.list_for_owner(
        owner_type, owner_id, limit, offset
    )
    return IncomeEntryMapper.to_response_list(entries)


# ============================================================
# Expenses
# ============================================================

@router.post("/expenses", response_model=ExpenseResponse)
@limiter.limit("30/minute")
async def log_expense(
    response: Response,
    request: Request,
    payload: ExpenseCreate,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_FINANCE)),
):
    owner_type, owner_id = _owner(user, ctx)

    expense = await get_container().expense_service.create(
        owner_type=owner_type,
        owner_id=owner_id,
        amount=payload.amount,
        description=payload.description,
        category=payload.category,
        currency=payload.currency,
        expense_date=payload.expense_date,
    )
    return ExpenseMapper.to_response(expense)


@router.get("/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    limit: int = 50,
    offset: int = 0,
):
    owner_type, owner_id = _owner(user, ctx)
    expenses = await get_container().expense_service.list_for_owner(
        owner_type, owner_id, limit, offset
    )
    return ExpenseMapper.to_response_list(expenses)


# ============================================================
# Budget
# ============================================================

@router.get("/budget", response_model=BudgetSummaryResponse)
async def get_budget(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    owner_type, owner_id = _owner(user, ctx)
    period_month = datetime.now(timezone.utc).date().replace(day=1)

    categories = await get_container().planning_service.budget_for_period(
        owner_type, owner_id, period_month
    )
    responses = BudgetCategoryMapper.to_response_list(categories)

    return BudgetSummaryResponse(
        period_month=period_month,
        categories=responses,
        total_limit=sum((c.monthly_limit for c in responses), start=0),
        total_spent=sum((c.spent for c in responses), start=0),
    )


# ============================================================
# Plan
# ============================================================

@router.get("/plan")
async def get_latest_plan(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    from app.repositories.finance.finance_repository import (
        AllocationPlanRepository,
    )
    from app.mappers.finance_mapper import AllocationPlanMapper

    owner_type, owner_id = _owner(user, ctx)
    plan = await get_container().planning_service.latest_plan(owner_type, owner_id)
    return AllocationPlanMapper.to_response(plan)


# ============================================================
# Recurring items / Debts / Goals (read-only listing)
# ============================================================

@router.get("/recurring-items", response_model=list[RecurringItemResponse])
async def list_recurring_items(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    owner_type, owner_id = _owner(user, ctx)
    items = await get_container().planning_service.recurring_items(owner_type, owner_id)
    return RecurringItemMapper.to_response_list(items)


@router.get("/debts", response_model=list[DebtResponse])
async def list_debts(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    owner_type, owner_id = _owner(user, ctx)
    debts = await get_container().planning_service.debts(owner_type, owner_id)
    return DebtMapper.to_response_list(debts)


@router.get("/goals", response_model=list[GoalResponse])
async def list_goals(
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    owner_type, owner_id = _owner(user, ctx)
    goals = await get_container().planning_service.goals(owner_type, owner_id)
    return GoalMapper.to_response_list(goals)


# ============================================================
# Personal Finance 2.0
#
# The five existing Supabase tables are the source of truth:
# financial_accounts, financial_transactions, financial_alerts,
# net_worth_snapshots and statement_imports.
#
# IMPORTANT: these tables are intentionally accessed through the
# backend service client. Their RLS remains enabled in Supabase;
# the backend authorization boundary is responsible for resolving
# the authenticated owner before every query.
# ============================================================


def _owner_values(user: AuthUser, ctx: OrganizationContext) -> tuple[str, str]:
    owner_type, owner_id = _owner(user, ctx)
    return (
        owner_type.value if hasattr(owner_type, "value") else str(owner_type),
        str(owner_id),
    )


def _cache_prefix(owner_type: str, owner_id: str) -> str:
    return f"finance:v2:{owner_type}:{owner_id}"


async def _db(loader):
    """Run the synchronous Supabase SDK off the event loop."""
    return await asyncio.to_thread(loader)


async def _invalidate_finance(owner_type: str, owner_id: str) -> None:
    await cache.delete_prefix(_cache_prefix(owner_type, owner_id))


@router.get("/summary")
@limiter.limit("60/minute")
async def finance_summary(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    ot, oid = _owner_values(user, ctx)
    key = f"{_cache_prefix(ot, oid)}:summary:{date.today().isoformat()}"

    async def load():
        month = date.today().replace(day=1)
        db = get_supabase()
        def query():
            income = db.table("income_entries").select("amount").eq("owner_type", ot).eq("owner_id", oid).gte("received_date", month.isoformat()).execute().data or []
            expenses = db.table("expenses").select("amount,category,expense_date,description").eq("owner_type", ot).eq("owner_id", oid).gte("expense_date", month.isoformat()).execute().data or []
            accounts = db.table("financial_accounts").select("id,name,account_type,institution_name,current_balance,available_balance,currency,is_manual,last_synced_at").eq("owner_type", ot).eq("owner_id", oid).eq("is_active", True).execute().data or []
            goals = db.table("goals").select("id,name,target_amount,current_amount,target_date,status").eq("owner_type", ot).eq("owner_id", oid).eq("status", "active").execute().data or []
            debts = db.table("debts").select("balance").eq("owner_type", ot).eq("owner_id", oid).execute().data or []
            return income, expenses, accounts, goals, debts
        income, expenses, accounts, goals, debts = await _db(query)
        total_income = sum((Decimal(str(x["amount"])) for x in income), Decimal("0"))
        total_spend = sum((Decimal(str(x["amount"])) for x in expenses), Decimal("0"))
        assets = sum((Decimal(str(x.get("current_balance") or 0)) for x in accounts if x.get("account_type") not in ("credit_card", "loan")), Decimal("0"))
        liabilities = sum((Decimal(str(x["balance"])) for x in debts), Decimal("0")) + sum((Decimal(str(x.get("current_balance") or 0)) for x in accounts if x.get("account_type") in ("credit_card", "loan")), Decimal("0"))
        categories: dict[str, float] = {}
        for row in expenses:
            category = row.get("category") or "other"
            categories[category] = categories.get(category, 0.0) + float(Decimal(str(row["amount"])))
        return {
            "month": month.isoformat(),
            "income": float(total_income),
            "spending": float(total_spend),
            "cash_flow": float(total_income - total_spend),
            "assets": float(assets),
            "liabilities": float(liabilities),
            "net_worth": float(assets - liabilities),
            "accounts": accounts,
            "active_goals": goals,
            "spending_by_category": categories,
        }

    return await cache.remember(key=key, ttl=30, loader=load)


@router.post("/accounts")
@limiter.limit("20/minute")
async def create_financial_account(
    response: Response,
    request: Request,
    payload: dict,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_FINANCE)),
):
    ot, oid = _owner_values(user, ctx)
    allowed = {"checking", "savings", "cash", "credit_card", "investment", "retirement", "loan", "other"}
    typ = payload.get("account_type", "checking")
    name = str(payload.get("name", "My account")).strip()
    if typ not in allowed:
        raise HTTPException(422, "Invalid account type")
    if not name or len(name) > 120:
        raise HTTPException(422, "Account name must be between 1 and 120 characters")
    balance = Decimal(str(payload.get("current_balance", 0)))
    if balance < 0:
        raise HTTPException(422, "Account balance cannot be negative")
    row = {
        "owner_type": ot, "owner_id": oid, "name": name, "account_type": typ,
        "institution_name": payload.get("institution_name"), "currency": payload.get("currency", "USD"),
        "current_balance": str(balance), "available_balance": payload.get("available_balance"), "is_manual": True,
    }
    result = await _db(lambda: get_supabase().table("financial_accounts").insert(row).execute().data[0])
    await _invalidate_finance(ot, oid)
    return result


@router.get("/accounts")
@limiter.limit("120/minute")
async def list_financial_accounts(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    ot, oid = _owner_values(user, ctx)
    key = f"{_cache_prefix(ot, oid)}:accounts"
    async def load():
        return await _db(lambda: get_supabase().table("financial_accounts").select("*").eq("owner_type", ot).eq("owner_id", oid).eq("is_active", True).order("created_at", desc=True).execute().data or [])
    return await cache.remember(key=key, ttl=30, loader=load)


@router.post("/transactions")
@limiter.limit("60/minute")
async def create_transaction(
    response: Response,
    request: Request,
    payload: dict,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(MANAGE_FINANCE)),
):
    ot, oid = _owner_values(user, ctx)
    typ = payload.get("transaction_type", "expense")
    if typ not in {"income", "expense", "transfer", "adjustment"}:
        raise HTTPException(422, "Invalid transaction type")
    try:
        amount = Decimal(str(payload.get("amount", 0)))
    except Exception as exc:
        raise HTTPException(422, "Invalid transaction amount") from exc
    if amount < 0:
        raise HTTPException(422, "Transaction amount cannot be negative")
    account_id = payload.get("account_id")
    if account_id:
        owned = await _db(lambda: get_supabase().table("financial_accounts").select("id").eq("id", account_id).eq("owner_type", ot).eq("owner_id", oid).eq("is_active", True).limit(1).execute().data)
        if not owned:
            raise HTTPException(404, "Financial account not found")
    row = {
        "owner_type": ot, "owner_id": oid, "account_id": account_id,
        "transaction_type": typ, "amount": str(amount), "currency": payload.get("currency", "USD"),
        "merchant": payload.get("merchant"), "description": payload.get("description"), "category": payload.get("category"),
        "transaction_date": payload.get("transaction_date") or date.today().isoformat(), "pending": bool(payload.get("pending", False)),
        "external_id": payload.get("external_id"), "metadata": payload.get("metadata") or {},
    }
    try:
        result = await _db(lambda: get_supabase().table("financial_transactions").insert(row).execute().data[0])
    except Exception as exc:
        # Preserve database uniqueness semantics for imported/external transactions.
        if "uq_financial_tx_external" in str(exc) or "duplicate key" in str(exc).lower():
            raise HTTPException(409, "A transaction with this external id already exists") from exc
        raise
    await _invalidate_finance(ot, oid)
    return result


@router.get("/transactions")
@limiter.limit("120/minute")
async def list_transactions(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=120),
):
    ot, oid = _owner_values(user, ctx)
    # Search results are short-lived; pagination stays out of cache keys when no search is used.
    key = f"{_cache_prefix(ot, oid)}:transactions:{limit}:{offset}:{search or ''}"
    async def load():
        def query():
            q = get_supabase().table("financial_transactions").select("*").eq("owner_type", ot).eq("owner_id", oid).order("transaction_date", desc=True).range(offset, offset + limit - 1)
            if search:
                q = q.or_(f"description.ilike.%{search}%,merchant.ilike.%{search}%")
            return q.execute().data or []
        return await _db(query)
    return await cache.remember(key=key, ttl=15, loader=load)


@router.get("/alerts")
@limiter.limit("120/minute")
async def list_financial_alerts(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    ot, oid = _owner_values(user, ctx)
    key = f"{_cache_prefix(ot, oid)}:alerts"
    async def load():
        return await _db(lambda: get_supabase().table("financial_alerts").select("*").eq("owner_type", ot).eq("owner_id", oid).eq("is_dismissed", False).order("created_at", desc=True).limit(20).execute().data or [])
    return await cache.remember(key=key, ttl=20, loader=load)


@router.get("/net-worth")
@limiter.limit("120/minute")
async def net_worth_history(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
    _permission: None = Depends(require_permission(VIEW_FINANCE)),
):
    ot, oid = _owner_values(user, ctx)
    key = f"{_cache_prefix(ot, oid)}:net-worth"
    async def load():
        return await _db(lambda: get_supabase().table("net_worth_snapshots").select("*").eq("owner_type", ot).eq("owner_id", oid).order("snapshot_date", desc=True).limit(24).execute().data or [])
    return await cache.remember(key=key, ttl=60, loader=load)


@router.get("/statement-reminder")
@limiter.limit("60/minute")
async def statement_reminder(
    response: Response,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    ctx: OrganizationContext = Depends(get_org_context),
):
    if not ctx.feature_flags.get("personal_mode", False):
        return {"due": False, "mode": "business"}
    ot, oid = _owner_values(user, ctx)
    key = f"{_cache_prefix(ot, oid)}:statement-reminder"

    async def load():
        rows = await _db(lambda: get_supabase().table("statement_imports").select("created_at,statement_end").eq("owner_type", ot).eq("owner_id", oid).order("created_at", desc=True).limit(1).execute().data or [])
        last = None
        if rows:
            try:
                last = datetime.fromisoformat(str(rows[0]["created_at"]).replace("Z", "+00:00"))
            except Exception:
                last = None
        days = (datetime.now(timezone.utc) - last).days if last else 999
        due = days >= 7
        return {
            "due": due, "days_since_import": days if last else None, "cadence": "weekly",
            "last_statement_end": rows[0].get("statement_end") if rows else None,
            "message": "Upload this week's statement so insights stay current." if due else "Your statement data is current.",
        }
    return await cache.remember(key=key, ttl=60, loader=load)
