"""
============================================================
app/services/export/export_result.py

Export Result

Shared return model for all exporters.
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExportResult:
    """
    Result returned by every exporter.
    """

    success: bool

    # For file exports
    file_bytes: bytes | None = None

    filename: str | None = None

    content_type: str | None = None

    # For Google Sheets exports
    url: str | None = None

    # Optional message
    message: str | None = None