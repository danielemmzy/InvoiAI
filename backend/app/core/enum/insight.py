"""
============================================================
Insight Enums

Backing Flow 10 (Finance Engine: Insight Pipeline).
Must be mirrored in PostgreSQL before deployment.
============================================================
"""

from enum import StrEnum


class InsightType(StrEnum):
    OVERDUE = "overdue"
    PRICE_INCREASE = "price_increase"
    ANOMALY = "anomaly"
    CASHFLOW = "cashflow"
    DUPLICATE = "duplicate"


class InsightSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
