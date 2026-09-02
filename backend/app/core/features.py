"""
============================================================
app/core/features.py

System feature flags.

Every premium capability in InvoiAI is represented here.

Plans grant access to features.

Permissions determine WHO may use them.

Never hardcode feature names.

Example

ctx.require_feature(Features.FINANCE_COPILOT)

============================================================
"""

from enum import StrEnum


class Features(StrEnum):

    # ========================================================
    # Core Platform
    # ========================================================

    DOCUMENT_UPLOAD = "document_upload"

    OCR = "ocr"

    AI_ANALYSIS = "ai_analysis"

    AI_CHAT = "ai_chat"

    AI_MEMORY = "ai_memory"

    VENDOR_MEMORY = "vendor_memory"

    ORGANIZATION_MEMORY = "organization_memory"

    DOCUMENT_SEARCH = "document_search"

    DOCUMENT_EXPORT = "document_export"

    DOCUMENT_SHARING = "document_sharing"

    # ========================================================
    # AI
    # ========================================================

    EMBEDDINGS = "embeddings"

    VECTOR_SEARCH = "vector_search"

    FINANCE_COPILOT = "finance_copilot"

    SEMANTIC_SEARCH = "semantic_search"

    DOCUMENT_CLASSIFICATION = "document_classification"

    ANOMALY_DETECTION = "anomaly_detection"

    FRAUD_DETECTION = "fraud_detection"

    DUPLICATE_DETECTION = "duplicate_detection"

    # ========================================================
    # Verification
    # ========================================================

    APPROVAL_WORKFLOWS = "approval_workflows"

    CUSTOM_WORKFLOWS = "custom_workflows"

    APPROVAL_ENGINE = "approval_engine"

    POLICY_ENGINE = "policy_engine"

    # ========================================================
    # Analytics
    # ========================================================

    DASHBOARD = "dashboard"

    ADVANCED_ANALYTICS = "advanced_analytics"

    REPORTS = "reports"

    CUSTOM_REPORTS = "custom_reports"

    # ========================================================
    # Integrations
    # ========================================================

    QUICKBOOKS = "quickbooks"

    XERO = "xero"

    GOOGLE_DRIVE = "google_drive"

    OUTLOOK = "outlook"

    GMAIL = "gmail"

    API_ACCESS = "api_access"

    WEBHOOKS = "webhooks"

    # ========================================================
    # Security
    # ========================================================

    AUDIT_LOGS = "audit_logs"

    RBAC = "rbac"

    SSO = "sso"

    SCIM = "scim"

    MFA = "mfa"

    # ========================================================
    # Infrastructure
    # ========================================================

    BACKGROUND_JOBS = "background_jobs"

    PRIORITY_QUEUE = "priority_queue"

    CACHE = "cache"

    REDIS = "redis"

    # ========================================================
    # Administration
    # ========================================================

    TEAM_MANAGEMENT = "team_management"

    ORGANIZATION_SETTINGS = "organization_settings"

    BILLING = "billing"

    USAGE_MONITORING = "usage_monitoring"

    # ========================================================
    # AP Automation — added for the 5-tier pricing model
    # (see core/plan.py). Each maps to a real, distinct
    # capability difference between tiers, not a marketing label.
    # ========================================================

    # AI-assisted GL coding (rules + vendor history + model fallback).
    # Without this, coding falls back to deterministic rules only —
    # still functional, just no AI suggestion tier.
    AI_GL_CODING = "ai_gl_coding"

    # 3-way matching (invoice + PO + goods receipt). Every plan gets
    # 2-way matching (invoice + PO); this is the upgrade beyond it.
    THREE_WAY_MATCHING = "three_way_matching"

    # Writing approved bills back to QuickBooks/Xero. Every plan gets
    # read-only sync; this is what makes it two-way.
    BILL_SYNC_WRITE = "bill_sync_write"

    # A secure, per-org email address vendors can send invoices to
    # directly, instead of manual upload only.
    EMAIL_INTAKE = "email_intake"

    # The daily proactive analyzer feed (cash runway, overdue
    # invoices, price hikes, duplicates) — see routers/insights.py.
    INSIGHTS_FEED = "insights_feed"

    # Structured queue for match/coding exceptions with review actions,
    # beyond just seeing a flagged document in the normal document list.
    EXCEPTION_QUEUE = "exception_queue"

    # Vendor-level analytics + cash flow views, beyond basic vendor list.
    VENDOR_ANALYTICS = "vendor_analytics"

    # Configurable price/quantity variance tolerances for matching,
    # instead of a fixed system default.
    TOLERANCE_ENGINE = "tolerance_engine"

    # Extra verification/hold when a vendor's bank details change —
    # a common fraud vector this specifically guards against.
    VENDOR_BANK_CHANGE_CONTROLS = "vendor_bank_change_controls"

    EXCEL_EXPORT = "excel_export"

    SHEETS_EXPORT = "sheets_export"

    MULTIPLE_BUSINESS_WORKSPACES = "multiple_business_workspaces"

    DEPARTMENT_BUDGETS = "department_budgets"

    SEGREGATION_OF_DUTIES = "segregation_of_duties"

    CUSTOM_CODING_RULES = "custom_coding_rules"

    WEEKLY_AI_DIGEST = "weekly_ai_digest"

    PRIORITY_SUPPORT = "priority_support"

    GUIDED_ONBOARDING = "guided_onboarding"

    MULTI_ORG_SUBSIDIARIES = "multi_org_subsidiaries"

    CUSTOM_ERP_INTEGRATIONS = "custom_erp_integrations"

    DEDICATED_SLA = "dedicated_sla"

    DATA_RESIDENCY = "data_residency"

    # Personal workspace tier
    PERSONAL_AI_ALLOCATION_PLANNER = "personal_ai_allocation_planner"

    PERSONAL_BANK_STATEMENT_IMPORT = "personal_bank_statement_import"

    PERSONAL_AI_ADVISOR = "personal_ai_advisor"

    PERSONAL_GOALS_DEBT_TRACKING = "personal_goals_debt_tracking"