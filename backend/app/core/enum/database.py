"""
============================================================
Database Enums

These enums MUST mirror PostgreSQL enums exactly.

Never add values here unless the PostgreSQL enum
has been updated first.

Used by:
- Domain models
- Repositories
- Services
============================================================
"""

from enum import StrEnum


# ============================================================
# Organization
# ============================================================

class OrgRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    APPROVER = "approver"


class PlanType(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


# ============================================================
# Documents
# ============================================================

class DocumentType(StrEnum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    QUOTATION = "quotation"
    CONTRACT = "contract"
    BANK_STATEMENT = "bank_statement"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    EXPENSE_REPORT = "expense_report"
    DELIVERY_NOTE = "delivery_note"
    PAYSLIP = "payslip"
    TAX_DOCUMENT = "tax_document"
    AUDIT_REPORT = "audit_report"
    FINANCIAL_STATEMENT = "financial_statement"
    CSV_EXPORT = "csv_export"
    SPREADSHEET = "spreadsheet"
    UNKNOWN = "unknown"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    OCR_RUNNING = "ocr_running"
    OCR_COMPLETE = "ocr_complete"
    ANALYSIS_RUNNING = "analysis_running"
    NEEDS_REVIEW = "needs_review"
    IN_APPROVAL = "in_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class PipelineStage(StrEnum):
    INTAKE = "intake"
    OCR = "ocr"
    AI_ANALYSIS = "ai_analysis"
    APPROVAL = "approval"
    COMPLETE = "complete"
    FAILED = "failed"


class DocumentSource(StrEnum):
    MANUAL = "manual"
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAGE = "sage"
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    GOOGLE_DRIVE = "google_drive"
    API = "api"
    WEBHOOK = "webhook"
    EMAIL_FORWARD = "email_forward"



class FileType(StrEnum):
    PDF = "pdf"

    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    TIFF = "tiff"
    BMP = "bmp"
    GIF = "gif"
    HEIC = "heic"
    HEIF = "heif"

    CSV = "csv"
    XLS = "xls"
    XLSX = "xlsx"
    XLSM = "xlsm"
    ODS = "ods"

    DOCX = "docx"
    ODT = "odt"

    XML = "xml"
    JSON = "json"
    TXT = "txt"

    EML = "eml"
    MSG = "msg"

    ZIP = "zip"


# ============================================================
# AI
# ============================================================

class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationType(StrEnum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"
    ESCALATE = "escalate"


# ============================================================
# Approval
# ============================================================

class ApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"
    ESCALATED = "escalated"
    SKIPPED = "skipped"


# ============================================================
# Integrations
# ============================================================

class IntegrationProvider(StrEnum):
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAGE = "sage"


# ============================================================
# Background Jobs
# ============================================================

class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(StrEnum):
    OCR_EXTRACTION = "ocr_extraction"
    AI_ANALYSIS = "ai_analysis"
    VENDOR_PROFILE_UPDATE = "vendor_profile_update"
    VENDOR_MEMORY_UPDATE = "vendor_memory_update"
    ORG_MEMORY_UPDATE = "org_memory_update"
    EMBEDDING_GENERATION = "embedding_generation"
    DUPLICATE_SCAN = "duplicate_scan"
    QUICKBOOKS_SYNC = "quickbooks_sync"
    XERO_SYNC = "xero_sync"
    SAGE_SYNC = "sage_sync"
    EMAIL_SYNC = "email_sync"
    TOKEN_REFRESH = "token_refresh"
    REPORT_GENERATION = "report_generation"
    BULK_EXPORT = "bulk_export"
    APPROVAL_REMINDER = "approval_reminder"
    APPROVAL_ESCALATION = "approval_escalation"


# ============================================================
# Fraud Detection
# ============================================================

class FraudSignal(StrEnum):
    AMOUNT_SPIKE = "amount_spike"
    NEW_VENDOR = "new_vendor"
    BANK_ACCOUNT_CHANGE = "bank_account_change"
    DUPLICATE_DOCUMENT = "duplicate_document"
    WEEKEND_DOCUMENT = "weekend_document"
    ROUND_NUMBER_AMOUNT = "round_number_amount"
    MISSING_CRITICAL_FIELDS = "missing_critical_fields"
    VENDOR_BLACKLISTED = "vendor_blacklisted"
    SEQUENTIAL_NUMBERS = "sequential_numbers"
    PO_MISMATCH = "po_mismatch"
    TAX_RATE_ANOMALY = "tax_rate_anomaly"
    CURRENCY_MISMATCH = "currency_mismatch"
    SPLIT_INVOICE = "split_invoice"
    GHOST_VENDOR = "ghost_vendor"
    UNUSUAL_PAYMENT_TERMS = "unusual_payment_terms"
    MULTIPLE_SUBMISSIONS = "multiple_submissions"

# ============================================================
# OCR Engine
# ============================================================

class OCREngineType(StrEnum):
    PDFPLUMBER = "pdfplumber"
    GPT4O_VISION = "gpt4o_vision"
    TEXTRACT = "textract"
    TESSERACT = "tesseract"
    GOOGLE_DOCUMENT_AI = "google_document_ai"

# ============================================================
# Integration Sync Status
# ============================================================

class IntegrationSyncStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================
# Integration Sync Type
# ============================================================

class IntegrationSyncType(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"
    MANUAL = "manual"
    WEBHOOK = "webhook"


# ============================================================
# Invoice Status
# ============================================================

class InvoiceStatus(StrEnum):
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

# ============================================================
# Subscription Status
# ============================================================

class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"