from enum import StrEnum

class InvoiceAPStatus(StrEnum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    MATCHING = "matching"
    CODING = "coding"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    SYNCING_TO_ERP = "syncing_to_erp"
    PAYMENT_READY = "payment_ready"
    PAID = "paid"
    RECONCILED = "reconciled"
    MATCH_EXCEPTION = "match_exception"
    CODING_EXCEPTION = "coding_exception"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"

class APExceptionType(StrEnum):
    PRICE_MISMATCH = "price_mismatch"
    QUANTITY_MISMATCH = "quantity_mismatch"
    MISSING_PO = "missing_po"
    MISSING_RECEIPT = "missing_receipt"
    DUPLICATE_INVOICE = "duplicate_invoice"
    UNKNOWN_VENDOR = "unknown_vendor"
    BANK_ACCOUNT_CHANGE = "bank_account_change"
    INVALID_TAX = "invalid_tax"
    GL_CODING_REQUIRED = "gl_coding_required"
    BUDGET_EXCEEDED = "budget_exceeded"
    CURRENCY_MISMATCH = "currency_mismatch"
    AMOUNT_EXCEEDS_PO = "amount_exceeds_po"
    VENDOR_BLOCKED = "vendor_blocked"
    COMPLIANCE_VIOLATION = "compliance_violation"

class APExceptionStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    WAIVED = "waived"
    ESCALATED = "escalated"

class APMatchStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    MATCHED = "matched"
    PARTIAL_MATCH = "partial_match"
    EXCEPTION = "exception"

class APCodingSource(StrEnum):
    RULE = "rule"
    HISTORICAL = "historical"
    AI_SUGGESTED = "ai_suggested"
    MANUAL = "manual"

class APCodingStatus(StrEnum):
    PENDING = "pending"
    AUTO_CODED = "auto_coded"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"

class APDimensionType(StrEnum):
    DEPARTMENT = "department"
    COST_CENTER = "cost_center"
    PROJECT = "project"
    LOCATION = "location"
    CLASS = "class"
    CUSTOM = "custom"
