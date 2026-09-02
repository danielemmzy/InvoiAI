"""
============================================================
Application Enums

These enums DO NOT mirror PostgreSQL.

They are used only inside the application.

Examples:
- AI providers
- OCR engines
- Chat roles
- Subscription lifecycle
- Workflow state
- Audit actions

If an enum is persisted in PostgreSQL,
it belongs in database.py instead.
============================================================
"""

from enum import StrEnum


# ============================================================
# AI
# ============================================================

class AIProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class OCREngine(StrEnum):
    GPT4O_VISION = "gpt4o_vision"
    PDFPLUMBER = "pdfplumber"
    TESSERACT = "tesseract"
    TEXTRACT = "textract"


# ============================================================
# Subscription
# ============================================================

class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"
    PAUSED = "paused"


# ============================================================
# Approval Workflow
# ============================================================

class ApprovalStatus(StrEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


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
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    RESTORE = "restore"

# ============================================================
# Integrations
# ============================================================

class IntegrationStatus(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"