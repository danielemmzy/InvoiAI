from typing import Final

# ============================================================
# Application
# ============================================================

APP_NAME: Final = "InvoiAI"
COMPANY_NAME: Final = "InvoiAI"
API_PREFIX: Final = "/api/v1"

# ============================================================
# Localization
# ============================================================

DEFAULT_LANGUAGE: Final = "en"
DEFAULT_TIMEZONE: Final = "UTC"
DEFAULT_CURRENCY: Final = "USD"

# ============================================================
# Pagination
# ============================================================

DEFAULT_PAGE_SIZE: Final = 25
MAX_PAGE_SIZE: Final = 100

# ============================================================
# IDs
# ============================================================

UUID_LENGTH: Final = 36
MAX_SLUG_LENGTH: Final = 100

# ============================================================
# Date Formats
# ============================================================

DATE_FORMAT: Final = "%Y-%m-%d"
DATETIME_FORMAT: Final = "%Y-%m-%d %H:%M:%S"

# ============================================================
# Document Types
# ============================================================

SUPPORTED_DOCUMENT_TYPES: Final = (
    "invoice",
    "receipt",
    "purchase_order",
    "quotation",
    "contract",
    "credit_note",
    "debit_note",
    "bank_statement",
    "spreadsheet",
    "csv",
    "expense_report",
    "delivery_note",
    "other",
)

# ============================================================
# Storage
# ============================================================

DOCUMENT_BUCKET: Final = "documents"

MAX_FILENAME_LENGTH: Final = 255

# ============================================================
# Redis Queue Names
# ============================================================

OCR_QUEUE: Final = "ocr"

AI_ANALYSIS_QUEUE: Final = "analysis"

EMBEDDING_QUEUE: Final = "embedding"

INTEGRATION_QUEUE: Final = "integration"

EMAIL_QUEUE: Final = "email"

NOTIFICATION_QUEUE: Final = "notification"

EXPORT_QUEUE: Final = "export"

WEBHOOK_QUEUE: Final = "webhook"

# ============================================================
# Job Status
# ============================================================

JOB_PENDING: Final = "pending"

JOB_RUNNING: Final = "running"

JOB_COMPLETED: Final = "completed"

JOB_FAILED: Final = "failed"

JOB_RETRYING: Final = "retrying"

# ============================================================
# Cache Keys
# ============================================================

CACHE_ORG_PREFIX: Final = "org"

CACHE_VENDOR_PREFIX: Final = "vendor"

CACHE_DOCUMENT_PREFIX: Final = "document"

CACHE_SETTINGS_PREFIX: Final = "settings"

# ============================================================
# AI
# ============================================================

DEFAULT_EMBEDDING_DIMENSION: Final = 1536

MAX_AI_RETRIES: Final = 3

AI_TIMEOUT_SECONDS: Final = 120

# ============================================================
# Audit
# ============================================================

REQUEST_ID_HEADER: Final = "X-Request-ID"

ORG_HEADER: Final = "X-Org-Id"

# ============================================================
# Background Workers
# ============================================================

DEFAULT_JOB_PRIORITY: Final = 5

MAX_JOB_RETRIES: Final = 3