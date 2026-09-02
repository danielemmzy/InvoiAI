"""
============================================================
app/core/plan.py

Subscription plan definitions.

Single source of truth for:

- pricing
- quotas
- limits
- enabled features
- plan helpers

Never hardcode plan limits, prices, or feature access anywhere
else — read them from here (get_plan / supports_feature /
PLANS). Two real bugs existed before this file was corrected:

  1. This module imported `Feature` from core.features, which
     only ever defined `Features` (plural). The import has always
     failed at runtime, so nothing in the app actually consumed
     this module — it was dead code silently.
  2. organization_service.create_workspace() hardcoded
     `document_limit: 10` for every new org regardless of plan,
     and stripe_event_processor.py had its own separate hardcoded
     {FREE: 0, STARTER: 100, PRO: 1000} map. Both now read from
     PLANS here instead, so there is exactly one place document
     limits are ever defined.

Pricing model: client-acquisition-first. Free is generous enough
to feel the real product (OCR, extraction, verification, one
approval, one QuickBooks/Xero connection) but not generous enough
to run a business on indefinitely — the AI GL coding, insights
feed, Copilot, and write-back to accounting stay behind Starter.
============================================================
"""

from dataclasses import dataclass, field
from typing import Final

from app.core.enum.database import PlanType
from app.core.features import Features

# ============================================================
# Plan Definition
# ============================================================


@dataclass(frozen=True)
class Plan:
    """
    Immutable subscription plan.
    """

    name: PlanType
    display_name: str

    # Pricing (USD). 0 for Free, and price_monthly/price_annual_monthly
    # are both 0 for Enterprise since it's contact-sales, not self-serve.
    price_monthly: int
    price_annual_monthly: int  # effective per-month price when billed annually
    contact_sales: bool = False

    # Seats
    seats: int = 1
    unlimited_seats: bool = False

    # Business workspace document limit (per month). This is the number
    # organizations.document_limit gets set to when an org is created or
    # changes plan — see organization_service.py and
    # services/billing/stripe_event_processor.py.
    monthly_documents: int = 0
    unlimited_documents: bool = False

    # How many accounting platforms can be connected simultaneously.
    # Free is 1 (QuickBooks OR Xero); Starter+ is both at once.
    max_accounting_integrations: int = 1

    # 2 or 3. Every plan gets 2-way (invoice vs PO); Pro+ adds 3-way
    # (invoice vs PO vs goods receipt).
    max_matching_ways: int = 2

    # How many business workspaces (orgs) one account can hold beyond
    # the first. 1 means "just the one you started with".
    max_business_workspaces: int = 1
    unlimited_business_workspaces: bool = False

    # How many files a single upload request may contain. This is not a
    # value-gate like monthly_documents — it exists so one request can't
    # dump an entire month's quota (or worse, hundreds of files) on the
    # OCR/analysis worker queue in one burst. It loosely tracks how much
    # real volume a tier is built to handle: Free's cap is intentionally
    # small relative to its 15/month quota so a single drag-and-drop
    # can't burn most of the month at once; paid tiers scale up with
    # their actual throughput needs. Enterprise is capped too — at that
    # point it's an infra/abuse ceiling, not a plan-fit one.
    max_batch_upload: int = 1

    export_formats: tuple[str, ...] = ("csv",)

    # Enabled capabilities beyond the quotas above.
    features: frozenset[Features] = field(default_factory=frozenset)


# ============================================================
# FREE — get them in the door
# ============================================================

FREE_PLAN = Plan(
    name=PlanType.FREE,
    display_name="Free",
    price_monthly=0,
    price_annual_monthly=0,
    seats=1,
    monthly_documents=15,
    max_accounting_integrations=1,
    max_matching_ways=2,
    max_business_workspaces=1,
    max_batch_upload=3,
    export_formats=("csv",),
    features=frozenset(
        {
            Features.DOCUMENT_UPLOAD,
            Features.OCR,
            Features.AI_ANALYSIS,
            Features.APPROVAL_WORKFLOWS,  # capped at 1 workflow — enforced at creation time, not here
            Features.QUICKBOOKS,
            Features.XERO,  # either/or — max_accounting_integrations=1 is what actually caps this
            Features.DASHBOARD,
        }
    ),
)

# ============================================================
# STARTER — $39/mo ($32/mo annual)
# ============================================================

STARTER_PLAN = Plan(
    name=PlanType.STARTER,
    display_name="Starter",
    price_monthly=39,
    price_annual_monthly=32,
    seats=3,
    monthly_documents=100,
    max_accounting_integrations=2,
    max_matching_ways=2,
    max_business_workspaces=1,
    max_batch_upload=10,
    export_formats=("csv", "excel", "sheets"),
    features=frozenset(
        {
            Features.DOCUMENT_UPLOAD,
            Features.OCR,
            Features.AI_ANALYSIS,
            Features.APPROVAL_WORKFLOWS,
            Features.CUSTOM_WORKFLOWS,  # multi-step approvals
            Features.QUICKBOOKS,
            Features.XERO,
            Features.AI_GL_CODING,
            Features.EXCEPTION_QUEUE,
            Features.BILL_SYNC_WRITE,
            Features.INSIGHTS_FEED,
            Features.FINANCE_COPILOT,
            Features.EXCEL_EXPORT,
            Features.SHEETS_EXPORT,
            Features.DASHBOARD,
            Features.VENDOR_MEMORY,
            Features.AUDIT_LOGS,
            # Personal workspace — everything unlimited from here up
            Features.PERSONAL_AI_ALLOCATION_PLANNER,
            Features.PERSONAL_BANK_STATEMENT_IMPORT,
            Features.PERSONAL_AI_ADVISOR,
            Features.PERSONAL_GOALS_DEBT_TRACKING,
        }
    ),
)

# ============================================================
# PRO — $119/mo ($109/mo annual)
# ============================================================

PRO_PLAN = Plan(
    name=PlanType.PRO,
    display_name="Pro",
    price_monthly=119,
    price_annual_monthly=109,
    seats=10,
    unlimited_documents=True,
    max_accounting_integrations=2,
    max_matching_ways=3,
    max_business_workspaces=3,
    max_batch_upload=25,
    export_formats=("csv", "excel", "sheets"),
    features=frozenset(
        STARTER_PLAN.features
        | {
            Features.THREE_WAY_MATCHING,
            Features.EMAIL_INTAKE,
            Features.VENDOR_ANALYTICS,
            Features.TOLERANCE_ENGINE,
            Features.VENDOR_BANK_CHANGE_CONTROLS,
            Features.ADVANCED_ANALYTICS,
            Features.API_ACCESS,
            Features.WEBHOOKS,
        }
    ),
)

# ============================================================
# BUSINESS — $349/mo ($279/mo annual)
# ============================================================

BUSINESS_PLAN = Plan(
    name=PlanType.BUSINESS,
    display_name="Business",
    price_monthly=349,
    price_annual_monthly=279,
    unlimited_seats=True,
    unlimited_documents=True,
    max_accounting_integrations=5,
    max_matching_ways=3,
    unlimited_business_workspaces=True,
    max_batch_upload=50,
    export_formats=("csv", "excel", "sheets"),
    features=frozenset(
        PRO_PLAN.features
        | {
            Features.MULTIPLE_BUSINESS_WORKSPACES,
            Features.MULTI_ORG_SUBSIDIARIES,
            Features.DEPARTMENT_BUDGETS,
            Features.SEGREGATION_OF_DUTIES,
            Features.CUSTOM_CODING_RULES,
            Features.WEEKLY_AI_DIGEST,
            Features.PRIORITY_SUPPORT,
            Features.GUIDED_ONBOARDING,
            Features.RBAC,
        }
    ),
)

# ============================================================
# ENTERPRISE — contact sales
# ============================================================

ENTERPRISE_PLAN = Plan(
    name=PlanType.ENTERPRISE,
    display_name="Enterprise",
    price_monthly=0,
    price_annual_monthly=0,
    contact_sales=True,
    unlimited_seats=True,
    unlimited_documents=True,
    max_accounting_integrations=999,
    max_matching_ways=3,
    unlimited_business_workspaces=True,
    max_batch_upload=100,
    export_formats=("csv", "excel", "sheets"),
    features=frozenset(
        BUSINESS_PLAN.features
        | {
            Features.SSO,
            Features.SCIM,
            Features.MFA,
            Features.CUSTOM_ERP_INTEGRATIONS,
            Features.DEDICATED_SLA,
            Features.DATA_RESIDENCY,
            Features.CUSTOM_REPORTS,
        }
    ),
)


# ============================================================
# Registry
# ============================================================

PLANS: Final[dict[PlanType, Plan]] = {
    PlanType.FREE: FREE_PLAN,
    PlanType.STARTER: STARTER_PLAN,
    PlanType.PRO: PRO_PLAN,
    PlanType.BUSINESS: BUSINESS_PLAN,
    PlanType.ENTERPRISE: ENTERPRISE_PLAN,
}


# ============================================================
# Helpers
# ============================================================


def get_plan(plan: PlanType | str) -> Plan:
    """
    Return a plan object.

    Example:
        plan = get_plan("pro")
    """
    return PLANS[PlanType(plan)]


def plan_exists(plan: str) -> bool:
    """
    Check if a plan exists.
    """
    try:
        PlanType(plan)
        return True
    except ValueError:
        return False


def is_paid_plan(plan: PlanType | str) -> bool:
    """
    True for Starter/Pro/Business/Enterprise.
    """
    return PlanType(plan) != PlanType.FREE


def supports_feature(
    plan: PlanType | str,
    feature: Features,
) -> bool:
    """
    Example:

        supports_feature(
            PlanType.PRO,
            Features.FINANCE_COPILOT,
        )
    """
    return feature in get_plan(plan).features


def document_limit_for(plan: PlanType | str) -> int:
    """
    The number to write into organizations.document_limit for a plan.
    Callers that need "no real cap" (unlimited_documents=True) should
    treat this as a very large practical ceiling, not literal infinity,
    so quota arithmetic elsewhere never has to special-case it.
    """
    p = get_plan(plan)
    return 999_999 if p.unlimited_documents else p.monthly_documents


def seat_limit_for(plan: PlanType | str) -> int:
    p = get_plan(plan)
    return 999_999 if p.unlimited_seats else p.seats


def batch_upload_limit_for(plan: PlanType | str) -> int:
    return get_plan(plan).max_batch_upload
