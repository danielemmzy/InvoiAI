"""
============================================================
app/core/enums.py

Shared application enums.

These enums mirror the PostgreSQL enums and should be used
throughout the backend instead of raw strings.

Never hardcode enum values in routers, services or repositories.
============================================================
"""

from enum import StrEnum


# ============================================================
# Organization
# ============================================================

class OrgRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    APPROVER = "approver"
    MEMBER = "member"
    VIEWER = "viewer"


# ============================================================
# Subscription Plans
# ============================================================

class PlanType(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ============================================================
# Document Status
# ============================================================

class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================
# Processing Pipeline
# ============================================================

class PipelineStage(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    OCR = "ocr"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    APPROVAL = "approval"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================
# Document Source
# ============================================================

class DocumentSource(StrEnum):
    MANUAL = "manual"
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    EMAIL = "email"
    GOOGLE_DRIVE = "google_drive"
    API = "api"


# ============================================================
# Document Type
# ============================================================

class DocumentType(StrEnum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    QUOTATION = "quotation"
    CONTRACT = "contract"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    BANK_STATEMENT = "bank_statement"
    SPREADSHEET = "spreadsheet"
    CSV = "csv"
    DELIVERY_NOTE = "delivery_note"
    EXPENSE_REPORT = "expense_report"
    OTHER = "other"


# ============================================================
# Risk
# ============================================================

class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# AI Recommendation
# ============================================================

class Recommendation(StrEnum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"


# ============================================================
# AI Provider
# ============================================================

class AIProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


# ============================================================
# Background Jobs
# ============================================================

class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    OCR = "ocr"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    EMBEDDING = "embedding"
    APPROVAL = "approval"
    SYNC = "sync"
    EMAIL = "email"
    EXPORT = "export"
    IMPORT = "import"
    WEBHOOK = "webhook"
    CLEANUP = "cleanup"


# ============================================================
# Integrations
# ============================================================

class IntegrationProvider(StrEnum):
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    GOOGLE_DRIVE = "google_drive"
    OUTLOOK = "outlook"
    GMAIL = "gmail"


class IntegrationStatus(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"


# ============================================================
# Approval
# ============================================================

class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    REQUEST_CHANGES = "request_changes"


# ============================================================
# Chat
# ============================================================

class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    DEVELOPER = "developer"


# ============================================================
# Audit
# ============================================================

class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"