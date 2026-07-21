"""
============================================================
app/core/plans.py

Subscription plan definitions.

Single source of truth for:

- quotas
- limits
- enabled features
- plan helpers

Never hardcode plan limits anywhere else.
============================================================
"""

from dataclasses import dataclass
from typing import Final

from backend.app.core.enum.enums import PlanType
from app.core.features import Feature


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

    # User limits
    max_users: int

    # Document limits
    monthly_documents: int
    storage_gb: int

    # AI limits
    ai_tokens_per_month: int

    # Integrations
    max_integrations: int

    # API
    api_requests_per_day: int

    # Queue
    max_background_jobs: int
    priority_queue: bool

    # Enabled capabilities
    features: frozenset[Feature]


# ============================================================
# FREE
# ============================================================

FREE_PLAN = Plan(
    name=PlanType.FREE,
    display_name="Free",

    max_users=1,
    monthly_documents=5,
    storage_gb=1,

    ai_tokens_per_month=50_000,

    max_integrations=0,

    api_requests_per_day=500,

    max_background_jobs=2,
    priority_queue=False,

    features=frozenset({
        Feature.OCR,
        Feature.DOCUMENT_UPLOAD,
    }),
)

# ============================================================
# STARTER
# ============================================================

STARTER_PLAN = Plan(
    name=PlanType.STARTER,
    display_name="Starter",

    max_users=5,
    monthly_documents=500,
    storage_gb=25,

    ai_tokens_per_month=500_000,

    max_integrations=3,

    api_requests_per_day=5_000,

    max_background_jobs=10,
    priority_queue=False,

    features=frozenset({
        Feature.OCR,
        Feature.DOCUMENT_UPLOAD,
        Feature.APPROVAL_WORKFLOWS,
        Feature.AUDIT_LOGS,
        Feature.VENDOR_MEMORY,
        Feature.FINANCE_COPILOT,
        Feature.QUICKBOOKS,
        Feature.XERO,
    }),
)

# ============================================================
# PRO
# ============================================================

PRO_PLAN = Plan(
    name=PlanType.PRO,
    display_name="Pro",

    max_users=25,
    monthly_documents=5_000,
    storage_gb=250,

    ai_tokens_per_month=5_000_000,

    max_integrations=20,

    api_requests_per_day=50_000,

    max_background_jobs=100,
    priority_queue=True,

    features=frozenset({
        Feature.OCR,
        Feature.DOCUMENT_UPLOAD,
        Feature.APPROVAL_WORKFLOWS,
        Feature.AUDIT_LOGS,
        Feature.VENDOR_MEMORY,
        Feature.FINANCE_COPILOT,
        Feature.QUICKBOOKS,
        Feature.XERO,
        Feature.CUSTOM_AI,
        Feature.CUSTOM_WORKFLOWS,
        Feature.VECTOR_SEARCH,
        Feature.WEBHOOKS,
    }),
)

# ============================================================
# ENTERPRISE
# ============================================================

ENTERPRISE_PLAN = Plan(
    name=PlanType.ENTERPRISE,
    display_name="Enterprise",

    max_users=999_999,
    monthly_documents=999_999_999,
    storage_gb=10_000,

    ai_tokens_per_month=999_999_999,

    max_integrations=999,

    api_requests_per_day=9_999_999,

    max_background_jobs=999_999,
    priority_queue=True,

    features=frozenset({
        Feature.OCR,
        Feature.DOCUMENT_UPLOAD,
        Feature.APPROVAL_WORKFLOWS,
        Feature.AUDIT_LOGS,
        Feature.VENDOR_MEMORY,
        Feature.FINANCE_COPILOT,
        Feature.QUICKBOOKS,
        Feature.XERO,
        Feature.CUSTOM_AI,
        Feature.CUSTOM_WORKFLOWS,
        Feature.VECTOR_SEARCH,
        Feature.WEBHOOKS,
        Feature.SSO,
        Feature.SCIM,
        Feature.UNLIMITED_USERS,
    }),
)


# ============================================================
# Registry
# ============================================================

PLANS: Final[dict[PlanType, Plan]] = {
    PlanType.FREE: FREE_PLAN,
    PlanType.STARTER: STARTER_PLAN,
    PlanType.PRO: PRO_PLAN,
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
    True for Starter/Pro/Enterprise.
    """
    return PlanType(plan) != PlanType.FREE


def supports_feature(
    plan: PlanType | str,
    feature: Feature,
) -> bool:
    """
    Example:

        supports_feature(
            PlanType.PRO,
            Feature.FINANCE_COPILOT,
        )
    """
    return feature in get_plan(plan).features