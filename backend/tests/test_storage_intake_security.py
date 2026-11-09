"""Ticket 5 — content validation, quarantine, and private storage contract."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.enum.database import DocumentSource, DocumentStatus, DocumentType, PipelineStage
from app.services.document.document_upload_service import DocumentUploadService
from app.services.storage.attachment_scanner import (
    EICAR_SIGNATURE,
    QUARANTINE_PREFIX,
    SignatureScanner,
)
from app.services.storage.file_inspection import (
    OversizedUploadError,
    SpoofedFileTypeError,
    UnsupportedFileContentError,
    detect_content_type,
    inspect_upload,
)


PDF_BYTES = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32


def test_content_detection_ignores_extension():
    assert detect_content_type(PDF_BYTES) == "application/pdf"
    assert detect_content_type(PNG_BYTES) == "image/png"
    assert detect_content_type(JPEG_BYTES) == "image/jpeg"
    assert detect_content_type(WEBP_BYTES) == "image/webp"
    assert detect_content_type(b"not a document") is None


def test_declared_type_must_match_content():
    with pytest.raises(SpoofedFileTypeError):
        inspect_upload(
            content=PDF_BYTES,
            declared_content_type="image/png",
            filename="invoice.pdf",
        )


def test_extension_must_match_content():
    with pytest.raises(SpoofedFileTypeError):
        inspect_upload(
            content=PDF_BYTES,
            declared_content_type="application/pdf",
            filename="invoice.png",
        )


def test_oversized_upload_is_rejected():
    with pytest.raises(OversizedUploadError):
        inspect_upload(
            content=PDF_BYTES,
            declared_content_type="application/pdf",
            filename="invoice.pdf",
            max_size_mb=0,
        )


def test_executable_content_is_rejected():
    with pytest.raises(UnsupportedFileContentError):
        inspect_upload(
            content=b"MZ" + b"\x00" * 64,
            declared_content_type="application/pdf",
            filename="invoice.pdf",
        )


def test_signature_scanner_flags_eicar_and_pdf_javascript():
    scanner = SignatureScanner()
    assert scanner.scan(content=b"%PDF-" + EICAR_SIGNATURE, filename="x.pdf").status == "infected"
    assert scanner.scan(content=b"%PDF-1.7 /JavaScript (alert(1))", filename="x.pdf").status == "policy_failed"
    assert scanner.scan(content=PDF_BYTES, filename="x.pdf").clean


class FakeDocumentService:
    def __init__(self):
        self.created = []

    async def find_duplicate(self, *_args, **_kwargs):
        return None

    async def create_document(self, document, allow_duplicate=False):
        self.created.append(document)
        return document


class FakeStorageService:
    def __init__(self):
        self.uploads = []
        self.deleted = []

    async def upload_document(self, *, path, content, content_type):
        self.uploads.append({"path": path, "content": content, "content_type": content_type})
        return path

    async def delete_document(self, path):
        self.deleted.append(path)


@pytest.fixture
def upload_service():
    documents = FakeDocumentService()
    storage = FakeStorageService()
    service = DocumentUploadService(
        document_service=documents,
        storage_service=storage,
    )
    return service, documents, storage


async def _upload(service, *, content, declared, filename):
    return await service.upload(
        org_id=uuid4(),
        user_id=uuid4(),
        filename=filename,
        content_type=declared,
        content=content,
        industry="general",
        document_type=DocumentType.INVOICE,
        currency="GBP",
    )


async def test_clean_pdf_is_stored_on_the_private_document_path(upload_service):
    service, documents, storage = upload_service

    document = await _upload(
        service,
        content=PDF_BYTES,
        declared="application/pdf",
        filename="invoice.pdf",
    )

    assert document.status == DocumentStatus.PENDING
    assert document.pipeline_stage == PipelineStage.INTAKE
    assert document.source == DocumentSource.MANUAL
    assert storage.uploads[0]["content_type"] == "application/pdf"
    assert not storage.uploads[0]["path"].startswith(QUARANTINE_PREFIX)
    assert storage.uploads[0]["path"].endswith("invoice.pdf")
    assert documents.created == [document]


async def test_infected_pdf_is_quarantined_and_never_enters_ocr(upload_service):
    service, documents, storage = upload_service
    infected = b"%PDF-1.7\n" + EICAR_SIGNATURE + b"\n%%EOF"

    document = await _upload(
        service,
        content=infected,
        declared="application/pdf",
        filename="invoice.pdf",
    )

    assert document.status == DocumentStatus.QUARANTINED
    assert document.pipeline_stage == PipelineStage.FAILED
    assert storage.uploads[0]["path"].startswith(f"{QUARANTINE_PREFIX}/")
    assert document.external_source_data["quarantine"]["signature"] == "eicar_test_file"
    assert document.validation_warnings
    # A quarantined document is persisted for operator visibility but its
    # status is not one the OCR worker ever picks up.
    assert documents.created == [document]
    assert document.status != DocumentStatus.PENDING


async def test_policy_failed_pdf_is_quarantined(upload_service):
    service, _documents, storage = upload_service

    document = await _upload(
        service,
        content=b"%PDF-1.7 /JavaScript (alert(1)) %%EOF",
        declared="application/pdf",
        filename="invoice.pdf",
    )

    assert document.status == DocumentStatus.QUARANTINED
    assert storage.uploads[0]["path"].startswith(f"{QUARANTINE_PREFIX}/")
    assert (
        document.external_source_data["quarantine"]["signature"]
        == "pdf_active_javascript"
    )


async def test_spoofed_upload_never_reaches_storage(upload_service):
    service, documents, storage = upload_service

    with pytest.raises(SpoofedFileTypeError):
        await _upload(
            service,
            content=PNG_BYTES,
            declared="application/pdf",
            filename="invoice.pdf",
        )

    assert storage.uploads == []
    assert documents.created == []


async def test_storage_failure_cleans_up_the_uploaded_object(upload_service):
    service, documents, storage = upload_service

    class FailingDocuments(FakeDocumentService):
        async def create_document(self, document, allow_duplicate=False):
            raise RuntimeError("database unavailable")

    service.documents = FailingDocuments()

    with pytest.raises(RuntimeError):
        await _upload(
            service,
            content=PDF_BYTES,
            declared="application/pdf",
            filename="invoice.pdf",
        )

    assert len(storage.deleted) == 1
