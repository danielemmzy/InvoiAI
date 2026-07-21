"""
============================================================
app/core/paths.py

Centralized storage path helpers.

Every document, export, AI artifact, and integration file
must use these helpers.

Never concatenate storage paths manually.

Storage layout

documents/
    {organization_id}/
        {user_id}/
            {document_id}/
                original.pdf
                thumbnail.png

============================================================
"""

from pathlib import PurePosixPath
from typing import Final


# ============================================================
# Storage Buckets
# ============================================================

DOCUMENT_BUCKET: Final = "documents"

EXPORT_BUCKET: Final = "exports"

TEMP_BUCKET: Final = "temp"

MODEL_BUCKET: Final = "models"


# ============================================================
# Root Folders
# ============================================================

DOCUMENTS_FOLDER: Final = "documents"

OCR_FOLDER: Final = "ocr"

ANALYSIS_FOLDER: Final = "analysis"

EMBEDDINGS_FOLDER: Final = "embeddings"

EXPORTS_FOLDER: Final = "exports"

THUMBNAILS_FOLDER: Final = "thumbnails"

ATTACHMENTS_FOLDER: Final = "attachments"

TEMP_FOLDER: Final = "temp"

LOGS_FOLDER: Final = "logs"

BACKUPS_FOLDER: Final = "backups"


# ============================================================
# Path Builders
# ============================================================

def document_path(
    organization_id: str,
    user_id: str,
    document_id: str,
    filename: str,
) -> str:
    """
    documents/{org}/{user}/{document}/{filename}
    """
    return str(
        PurePosixPath(
            organization_id,
            user_id,
            document_id,
            filename,
        )
    )


def thumbnail_path(
    organization_id: str,
    document_id: str,
    filename: str,
) -> str:
    """
    thumbnails/{org}/{document}/{filename}
    """
    return str(
        PurePosixPath(
            THUMBNAILS_FOLDER,
            organization_id,
            document_id,
            filename,
        )
    )


def ocr_path(
    organization_id: str,
    document_id: str,
) -> str:
    """
    ocr/{org}/{document}.json
    """
    return str(
        PurePosixPath(
            OCR_FOLDER,
            organization_id,
            f"{document_id}.json",
        )
    )


def analysis_path(
    organization_id: str,
    document_id: str,
) -> str:
    """
    analysis/{org}/{document}.json
    """
    return str(
        PurePosixPath(
            ANALYSIS_FOLDER,
            organization_id,
            f"{document_id}.json",
        )
    )


def embedding_path(
    organization_id: str,
    embedding_id: str,
) -> str:
    """
    embeddings/{org}/{embedding}.json
    """
    return str(
        PurePosixPath(
            EMBEDDINGS_FOLDER,
            organization_id,
            f"{embedding_id}.json",
        )
    )


def export_path(
    organization_id: str,
    export_id: str,
    filename: str,
) -> str:
    """
    exports/{org}/{export}/{filename}
    """
    return str(
        PurePosixPath(
            EXPORTS_FOLDER,
            organization_id,
            export_id,
            filename,
        )
    )


def temp_path(filename: str) -> str:
    """
    temp/{filename}
    """
    return str(
        PurePosixPath(
            TEMP_FOLDER,
            filename,
        )
    )


def log_path(filename: str) -> str:
    """
    logs/{filename}
    """
    return str(
        PurePosixPath(
            LOGS_FOLDER,
            filename,
        )
    )


def backup_path(
    organization_id: str,
    backup_name: str,
) -> str:
    """
    backups/{org}/{backup}.zip
    """
    return str(
        PurePosixPath(
            BACKUPS_FOLDER,
            organization_id,
            f"{backup_name}.zip",
        )
    )