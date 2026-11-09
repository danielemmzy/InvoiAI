"""
Content-based upload inspection.

Extensions and client-declared MIME types are attacker-controlled. A file is
accepted only when its magic bytes match one of the supported document types
and the declared type agrees with the detected type.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from app.core.config import settings
from app.core.enum.database import FileType


class UploadInspectionError(ValueError):
    """Base class for a rejected upload."""


class EmptyUploadError(UploadInspectionError):
    pass


class OversizedUploadError(UploadInspectionError):
    pass


class UnsupportedFileContentError(UploadInspectionError):
    pass


class SpoofedFileTypeError(UploadInspectionError):
    pass


@dataclass(frozen=True)
class UploadInspection:
    content_type: str
    file_type: FileType
    extension: str
    size_bytes: int


#: Canonical MIME -> (FileType, accepted extensions)
SUPPORTED_CONTENT: dict[str, tuple[FileType, frozenset[str]]] = {
    "application/pdf": (FileType.PDF, frozenset({"pdf"})),
    "image/jpeg": (FileType.JPEG, frozenset({"jpg", "jpeg"})),
    "image/png": (FileType.PNG, frozenset({"png"})),
    "image/webp": (FileType.WEBP, frozenset({"webp"})),
}


def detect_content_type(content: bytes) -> str | None:
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def inspect_upload(
    *,
    content: bytes,
    declared_content_type: str | None,
    filename: str | None,
    max_size_mb: int | None = None,
) -> UploadInspection:
    if not content:
        raise EmptyUploadError("Uploaded file is empty.")

    limit_mb = settings.max_file_size_mb if max_size_mb is None else max_size_mb
    if len(content) > limit_mb * 1024 * 1024:
        raise OversizedUploadError(f"File exceeds the {limit_mb}MB limit.")

    detected = detect_content_type(content)
    if detected is None or detected not in SUPPORTED_CONTENT:
        raise UnsupportedFileContentError(
            "File content is not a supported PDF, JPEG, PNG, or WebP document."
        )

    declared = (declared_content_type or "").lower().strip()
    if not declared:
        raise SpoofedFileTypeError("A declared content type is required.")

    # image/jpg is a common but non-standard alias; normalize it.
    if declared == "image/jpg":
        declared = "image/jpeg"

    if declared not in SUPPORTED_CONTENT:
        raise UnsupportedFileContentError(f"Unsupported file type: {declared}.")

    if declared != detected:
        raise SpoofedFileTypeError(
            f"Declared content type {declared} does not match the file content {detected}."
        )

    file_type, extensions = SUPPORTED_CONTENT[detected]
    extension = PurePath(filename or "").suffix.lower().lstrip(".")
    if extension and extension not in extensions:
        raise SpoofedFileTypeError(
            f"File extension .{extension} does not match the file content {detected}."
        )

    return UploadInspection(
        content_type=detected,
        file_type=file_type,
        extension=extension or next(iter(extensions)),
        size_bytes=len(content),
    )
