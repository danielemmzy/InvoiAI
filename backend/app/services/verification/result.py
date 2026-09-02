"""
============================================================
Verification Result

Shared return object for every verification module.

Every module returns one VerificationResult.

Examples
--------
OCR Validation
Math Check
Vendor Check
Fraud Check

The engine combines these into a final Analysis.
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VerificationResult:
    """
    Standard result returned by every
    verification module.
    """

    # -----------------------------------------
    # Overall
    # -----------------------------------------

    passed: bool

    score: int

    confidence: int

    # -----------------------------------------
    # Human-readable output
    # -----------------------------------------

    summary: str

    # -----------------------------------------
    # Evidence
    # -----------------------------------------

    reasons: list[str] = field(
        default_factory=list,
    )

    positives: list[str] = field(
        default_factory=list,
    )

    warnings: list[str] = field(
        default_factory=list,
    )

    # -----------------------------------------
    # Raw module data
    # -----------------------------------------

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )