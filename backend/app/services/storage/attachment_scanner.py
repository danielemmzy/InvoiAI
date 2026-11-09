"""
Attachment scanning seam.

The MVP ships a deterministic signature scanner so quarantine behaviour is
testable without an external service. Production must configure a real
anti-malware engine behind the same `AttachmentScanner` interface before
launch; until then the signature scanner still blocks known test/executable
content and active PDF JavaScript.

An infected or policy-failed attachment is stored under the quarantine prefix
and never enters OCR.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

ScanStatus = Literal["clean", "infected", "policy_failed"]

EICAR_SIGNATURE = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)

EXECUTABLE_MAGIC = (
    b"MZ",
    b"\x7fELF",
    b"\xcf\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xca\xfe\xba\xbe",
)

#: Stored inside the existing private bucket. Never a public bucket.
QUARANTINE_PREFIX = "quarantine"


@dataclass(frozen=True)
class ScanResult:
    status: ScanStatus
    signature: str | None = None
    reason: str | None = None

    @property
    def clean(self) -> bool:
        return self.status == "clean"


class AttachmentScanner(Protocol):
    def scan(self, *, content: bytes, filename: str | None) -> ScanResult: ...


class SignatureScanner:
    """Deterministic scanner used by the MVP and by contract tests."""

    def scan(self, *, content: bytes, filename: str | None) -> ScanResult:
        if EICAR_SIGNATURE in content:
            return ScanResult(
                status="infected",
                signature="eicar_test_file",
                reason="The attachment matches the EICAR antivirus test signature.",
            )

        for magic in EXECUTABLE_MAGIC:
            if content.startswith(magic):
                return ScanResult(
                    status="infected",
                    signature="executable_content",
                    reason="Executable content is not an accepted invoice attachment.",
                )

        if content.startswith(b"%PDF-") and (
            b"/JavaScript" in content or b"/JS" in content
        ):
            return ScanResult(
                status="policy_failed",
                signature="pdf_active_javascript",
                reason="PDF files with embedded JavaScript are not accepted.",
            )

        return ScanResult(status="clean")


_default_scanner: AttachmentScanner = SignatureScanner()


def get_attachment_scanner() -> AttachmentScanner:
    return _default_scanner
