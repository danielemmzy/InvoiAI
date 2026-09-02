from __future__ import annotations

from dataclasses import dataclass
import os

from google.cloud import documentai
from google.oauth2 import service_account

from app.core.config import settings


_GOOGLE_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def _google_credentials():
    """Build Google credentials from explicit service-account settings.

    Local development should not depend on `gcloud auth application-default login`.
    Production can still use GOOGLE_APPLICATION_CREDENTIALS when the explicit
    service-account fields are not configured.
    """
    if all(
        (
            settings.google_project_id,
            settings.google_private_key_id,
            settings.google_private_key,
            settings.google_service_account_email,
        )
    ):
        private_key = settings.google_private_key.replace("\\n", "\n")
        info = {
            "type": "service_account",
            "project_id": settings.google_project_id,
            "private_key_id": settings.google_private_key_id,
            "private_key": private_key,
            "client_email": settings.google_service_account_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=[_GOOGLE_CLOUD_PLATFORM_SCOPE],
        )

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if credentials_path:
        return service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=[_GOOGLE_CLOUD_PLATFORM_SCOPE],
        )

    raise RuntimeError(
        "Google Document AI is not configured. Set GOOGLE_PROJECT_ID, "
        "GOOGLE_PRIVATE_KEY_ID, GOOGLE_PRIVATE_KEY, and "
        "GOOGLE_SERVICE_ACCOUNT_EMAIL, or set GOOGLE_APPLICATION_CREDENTIALS."
    )


@dataclass(slots=True)
class OCRPage:
    page_number: int
    text: str


@dataclass(slots=True)
class OCRResponse:
    raw_text: str
    pages: list[OCRPage]
    tables_detected: list[dict]
    languages: list[str]
    confidence: float
    processing_document: documentai.Document


class GoogleDocumentAIService:
    """
    Google Document AI integration.

    Responsibilities
    ----------------
    • Send document to Google
    • Normalize Google response
    • Return provider-agnostic OCRResponse

    No persistence.
    No repositories.
    """

    def __init__(self) -> None:

        credentials = _google_credentials()
        self.client = documentai.DocumentProcessorServiceClient(
            credentials=credentials,
        )

        self.processor_name = self.client.processor_path(
            settings.google_project_id,
            settings.google_location,
            settings.google_processor_id,
        )

    # =====================================================
    # OCR
    # =====================================================

    def process_document(
        self,
        *,
        content: bytes,
        mime_type: str,
    ) -> OCRResponse:
        """
        Process a document using Google Document AI.
        """

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=documentai.RawDocument(
                content=content,
                mime_type=mime_type,
            ),
        )

        result = self.client.process_document(
            request=request,
        )

        document = result.document

        raw_text = document.text or ""

        pages: list[OCRPage] = []

        for index, page in enumerate(document.pages):

            page_text = ""

            anchor = page.layout.text_anchor

            if anchor.text_segments:

                for segment in anchor.text_segments:

                    start = int(segment.start_index or 0)
                    end = int(segment.end_index)

                    page_text += raw_text[start:end]

            pages.append(
                OCRPage(
                    page_number=index + 1,
                    text=page_text,
                )
            )

        tables: list[dict] = []

        for page in document.pages:

            for table in page.tables:

                tables.append(
                    {
                        "header_rows": len(table.header_rows),
                        "body_rows": len(table.body_rows),
                    }
                )

        languages: set[str] = set()

        for page in document.pages:

            for language in page.detected_languages:

                if language.language_code:
                    languages.add(language.language_code)

        confidences = [
            page.layout.confidence
            for page in document.pages
            if page.layout.confidence is not None
        ]

        confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else 0.0
        )

        return OCRResponse(
            raw_text=raw_text,
            pages=pages,
            tables_detected=tables,
            languages=sorted(languages),
            confidence=confidence,
            processing_document=document,
        )