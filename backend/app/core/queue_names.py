"""
============================================================
app/core/queue_names.py

Centralized background queue definitions.

Every background job MUST use one of these queues.

Never hardcode queue names anywhere in the application.

These queues are consumed by Redis workers
(Arq, Celery, Dramatiq, RQ, etc.)

Queue Flow

Upload
    │
    ▼
OCR Queue
    │
    ▼
Classification Queue
    │
    ▼
Extraction Queue
    │
    ▼
AI Analysis Queue
    │
    ▼
Embedding Queue
    │
    ▼
Analytics Queue
    │
    ▼
Completed

============================================================
"""

from typing import Final

# ============================================================
# Document Processing
# ============================================================

OCR_QUEUE: Final = "ocr"

CLASSIFICATION_QUEUE: Final = "classification"

EXTRACTION_QUEUE: Final = "extraction"

AI_ANALYSIS_QUEUE: Final = "analysis"

EMBEDDING_QUEUE: Final = "embedding"

DOCUMENT_EXPORT_QUEUE: Final = "document_export"


# ============================================================
# Finance Engines
# ============================================================

VERIFICATION_QUEUE: Final = "verification"

FRAUD_DETECTION_QUEUE: Final = "fraud_detection"

DUPLICATE_CHECK_QUEUE: Final = "duplicate_check"

VENDOR_MEMORY_QUEUE: Final = "vendor_memory"

FINANCIAL_MEMORY_QUEUE: Final = "financial_memory"

ANALYTICS_QUEUE: Final = "analytics"


# ============================================================
# Integrations
# ============================================================

QUICKBOOKS_SYNC_QUEUE: Final = "quickbooks_sync"

XERO_SYNC_QUEUE: Final = "xero_sync"

GOOGLE_DRIVE_SYNC_QUEUE: Final = "google_drive_sync"

EMAIL_IMPORT_QUEUE: Final = "email_import"

WEBHOOK_QUEUE: Final = "webhook"


# ============================================================
# Notifications
# ============================================================

EMAIL_QUEUE: Final = "email"

SMS_QUEUE: Final = "sms"

NOTIFICATION_QUEUE: Final = "notification"


# ============================================================
# AI
# ============================================================

COPILOT_QUEUE: Final = "finance_copilot"

CHAT_QUEUE: Final = "chat"

VECTOR_QUEUE: Final = "vector"

MEMORY_QUEUE: Final = "memory"


# ============================================================
# Background Maintenance
# ============================================================

CACHE_WARMUP_QUEUE: Final = "cache_warmup"

CACHE_CLEANUP_QUEUE: Final = "cache_cleanup"

FILE_CLEANUP_QUEUE: Final = "file_cleanup"

BACKUP_QUEUE: Final = "backup"

REPORT_QUEUE: Final = "report"

AUDIT_QUEUE: Final = "audit"


# ============================================================
# Priorities
# ============================================================

PRIORITY_CRITICAL: Final = 100

PRIORITY_HIGH: Final = 75

PRIORITY_NORMAL: Final = 50

PRIORITY_LOW: Final = 25


# ============================================================
# Retry Policy
# ============================================================

DEFAULT_MAX_RETRIES: Final = 3

MAX_AI_RETRIES: Final = 2

MAX_SYNC_RETRIES: Final = 5

MAX_EMAIL_RETRIES: Final = 5


# ============================================================
# Timeouts (seconds)
# ============================================================

OCR_TIMEOUT: Final = 300

ANALYSIS_TIMEOUT: Final = 600

EMBEDDING_TIMEOUT: Final = 300

SYNC_TIMEOUT: Final = 900

EXPORT_TIMEOUT: Final = 600


# ============================================================
# Queue Groups
# ============================================================

DOCUMENT_QUEUES: Final = (
    OCR_QUEUE,
    CLASSIFICATION_QUEUE,
    EXTRACTION_QUEUE,
    AI_ANALYSIS_QUEUE,
    EMBEDDING_QUEUE,
)

INTEGRATION_QUEUES: Final = (
    QUICKBOOKS_SYNC_QUEUE,
    XERO_SYNC_QUEUE,
    GOOGLE_DRIVE_SYNC_QUEUE,
)

MAINTENANCE_QUEUES: Final = (
    CACHE_CLEANUP_QUEUE,
    FILE_CLEANUP_QUEUE,
    BACKUP_QUEUE,
)

AI_QUEUES: Final = (
    AI_ANALYSIS_QUEUE,
    COPILOT_QUEUE,
    CHAT_QUEUE,
    VECTOR_QUEUE,
    MEMORY_QUEUE,
)