"""
============================================================
Personal Finance Enums

New enums backing Flow 8 (Personal Finance Logging) and
Flow 9 (Bank Statement Auto-Categorization).

These MUST be mirrored in PostgreSQL enums before this code
is deployed — see the migration note in
services/finance/planning_service.py.
============================================================
"""

from enum import StrEnum


class OwnerType(StrEnum):
    """
    Every personal-finance row is owned either by an
    organization (Business Mode) or directly by a user
    (Personal Mode) — see org.features.personal_mode.
    """

    ORGANIZATION = "organization"
    PERSONAL = "personal"


class IncomeSource(StrEnum):
    SALARY = "salary"
    FREELANCE = "freelance"
    BUSINESS = "business"
    INVESTMENT = "investment"
    GIFT = "gift"
    REFUND = "refund"
    OTHER = "other"


class ExpenseCategory(StrEnum):
    HOUSING = "housing"
    UTILITIES = "utilities"
    TRANSPORT = "transport"
    FOOD = "food"
    SUBSCRIPTIONS = "subscriptions"
    DEBT_PAYMENT = "debt_payment"
    SAVINGS = "savings"
    HEALTHCARE = "healthcare"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    EDUCATION = "education"
    INSURANCE = "insurance"
    OTHER = "other"


class RecurringFrequency(StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


class TransactionType(StrEnum):
    """Used by the bank-statement extractor (Flow 9)."""

    CREDIT = "credit"
    DEBIT = "debit"
