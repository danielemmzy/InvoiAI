"""
============================================================
app/core/mime_types.py

Centralized MIME type definitions for InvoiAI.

This module defines every file format the platform accepts.

Never hardcode MIME types anywhere else in the application.

Routers, validators, upload services, OCR pipelines and
integrations should import from here.

Example:
    from app.core.mime_types import ALLOWED_MIME_TYPES
============================================================
"""

from typing import Final

# ============================================================
# PDF
# ============================================================

PDF: Final = "application/pdf"

# ============================================================
# Images
# ============================================================

JPEG: Final = "image/jpeg"

JPG: Final = "image/jpg"

PNG: Final = "image/png"

WEBP: Final = "image/webp"

TIFF: Final = "image/tiff"

BMP: Final = "image/bmp"

HEIC: Final = "image/heic"

# ============================================================
# CSV
# ============================================================

CSV: Final = "text/csv"

CSV_ALT: Final = "application/csv"

# ============================================================
# Microsoft Excel
# ============================================================

XLS: Final = "application/vnd.ms-excel"

XLSX: Final = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ============================================================
# Word Documents
# ============================================================

DOC: Final = "application/msword"

DOCX: Final = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# ============================================================
# Text
# ============================================================

TXT: Final = "text/plain"

XML: Final = "application/xml"

JSON: Final = "application/json"

# ============================================================
# Archives
# ============================================================

ZIP: Final = "application/zip"

# ============================================================
# Allowed Upload Types
# ============================================================

ALLOWED_MIME_TYPES: Final = frozenset(
    {
        PDF,
        JPEG,
        JPG,
        PNG,
        WEBP,
        TIFF,
        BMP,
        HEIC,
        CSV,
        CSV_ALT,
        XLS,
        XLSX,
        DOC,
        DOCX,
        TXT,
        XML,
        JSON,
    }
)

# ============================================================
# OCR Supported Types
# ============================================================

OCR_SUPPORTED_MIME_TYPES: Final = frozenset(
    {
        PDF,
        JPEG,
        JPG,
        PNG,
        WEBP,
        TIFF,
        BMP,
        HEIC,
    }
)

# ============================================================
# Structured Data Types
# ============================================================

STRUCTURED_DATA_MIME_TYPES: Final = frozenset(
    {
        CSV,
        CSV_ALT,
        XLS,
        XLSX,
        JSON,
        XML,
    }
)

# ============================================================
# Office Documents
# ============================================================

OFFICE_DOCUMENT_MIME_TYPES: Final = frozenset(
    {
        DOC,
        DOCX,
        XLS,
        XLSX,
    }
)

# ============================================================
# Maximum Upload Sizes (MB)
# ============================================================

DEFAULT_MAX_UPLOAD_MB: Final = 25

MAX_IMAGE_UPLOAD_MB: Final = 15

MAX_DOCUMENT_UPLOAD_MB: Final = 25

MAX_SPREADSHEET_UPLOAD_MB: Final = 50

MAX_ARCHIVE_UPLOAD_MB: Final = 100