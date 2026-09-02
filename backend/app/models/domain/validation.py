"""
============================================================
Validation Result

Returned by ValidationService before AI analysis.
============================================================
"""

from __future__ import annotations

from pydantic import Field

from app.models.domain.base import DomainModel


class ValidationResult(DomainModel):
    """
    Result of document validation.
    """

    passed: bool

    warnings: list[str] = Field(default_factory=list)

    errors: list[str] = Field(default_factory=list)

    metadata: dict = Field(default_factory=dict)