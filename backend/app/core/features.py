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