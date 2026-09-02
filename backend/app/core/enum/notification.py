from __future__ import annotations

from enum import StrEnum


class NotificationType(StrEnum):
    """Stable application notification event identifiers."""

    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_DELEGATED = "approval_delegated"
    APPROVAL_ESCALATED = "approval_escalated"
    APPROVAL_COMPLETED = "approval_completed"

    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_FAILED = "document_failed"

    AI_COMPLETED = "ai_completed"
    AI_FAILED = "ai_failed"

    INVOICE_PAID = "invoice_paid"
    INVOICE_OVERDUE = "invoice_overdue"
    PAYMENT_FAILED = "payment_failed"

    INSIGHT_CRITICAL = "insight_critical"
    INTEGRATION_ERROR = "integration_error"
    FINANCE_BUDGET_RESET = "finance_budget_reset"
    FINANCE_RECURRING_DUE = "finance_recurring_due"
    FINANCE_GOAL_PROGRESS = "finance_goal_progress"
    FINANCE_STATEMENT_REMINDER = "finance_statement_reminder"

    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationPreferenceField(StrEnum):
    EMAIL = "email_enabled"
    IN_APP = "in_app_enabled"
    PUSH = "push_enabled"
    SMS = "sms_enabled"


class NotificationDeliveryStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class NotificationProvider(StrEnum):
    IN_APP = "in_app"
    SMTP = "smtp"
    RESEND = "resend"
    SENDGRID = "sendgrid"
    FCM = "fcm"
    TWILIO = "twilio"
