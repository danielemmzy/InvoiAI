"""
============================================================
Analyzer Result

Shared return object for every insight analyzer, mirroring
the pattern in services/verification/result.py. Detectors
consume this to decide whether to raise an Insight.
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AnalyzerResult:
    """
    Pure-Python analytics output — no LLM involved anywhere in
    an analyzer. Matches Flow 10's "ALL ANALYZERS RUN (pure
    Python math — NO LLM)".
    """

    name: str
    data: dict[str, Any] = field(default_factory=dict)
