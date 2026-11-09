from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from io import BytesIO

import httpx
from openai import AsyncOpenAI
from PIL import Image

from app.core.ai_config import EXTRACTION_MODEL
from app.core.config import settings


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


class OpenAIOCRService:
    """
    OpenAI OCR provider.

    Uses OpenAI vision to extract text from:
    - PNG
    - JPEG
    - WEBP

    PDFs are converted into page images before OCR.

    Returns a provider-agnostic OCRResponse so the existing
    OCR pipeline remains unchanged.
    """

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OpenAI OCR is not configured. "
                "Set OPENAI_API_KEY."
            )

        # OCR vision calls can take longer than ordinary chat requests,
        # especially for high-resolution scans and PDF pages. Keep connection
        # establishment bounded while allowing enough time for model inference.
        # BaseWorker owns document-level retries, so SDK retries stay disabled
        # to avoid multiplying long waits for each worker attempt.
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(
                90.0,
                connect=10.0,
                read=90.0,
                write=30.0,
                pool=10.0,
            ),
            max_retries=0,
        )

    # =====================================================
    # Public
    # =====================================================

    async def process_document(
        self,
        *,
        content: bytes,
        mime_type: str,
    ) -> OCRResponse:

        if not content:
            raise ValueError(
                "Document content cannot be empty."
            )

        if not mime_type:
            raise ValueError(
                "Document MIME type is required."
            )

        images = await asyncio.to_thread(
            self._prepare_images,
            content=content,
            mime_type=mime_type,
        )

        pages: list[OCRPage] = []
        languages: set[str] = set()
        tables_detected: list[dict] = []

        for page_number, image_data_url in enumerate(
            images,
            start=1,
        ):
            response = await self.client.chat.completions.create(
                model=EXTRACTION_MODEL,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an OCR engine. "
                            "Extract ALL visible text exactly as it "
                            "appears in the document. "
                            "Preserve reading order where possible. "
                            "Do not summarize. "
                            "Do not explain. "
                            "Return JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "OCR this document page and return "
                                    "exactly this JSON structure:\n"
                                    "{\n"
                                    '  "text": "all extracted text",\n'
                                    '  "language": "detected language code",\n'
                                    '  "has_table": true\n'
                                    "}\n\n"
                                    "Do not omit visible text."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_url,
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                response_format={
                    "type": "json_object",
                },
            )

            content_text = (
                response.choices[0]
                .message
                .content
                or "{}"
            )

            data = self._parse_response(
                content_text,
            )

            page_text = str(
                data.get("text")
                or ""
            ).strip()

            language = str(
                data.get("language")
                or ""
            ).strip()

            if language:
                languages.add(
                    language
                )

            if bool(
                data.get("has_table")
            ):
                tables_detected.append(
                    {
                        "page_number": page_number,
                    }
                )

            pages.append(
                OCRPage(
                    page_number=page_number,
                    text=page_text,
                )
            )

        raw_text = "\n\n".join(
            page.text
            for page in pages
            if page.text
        )

        return OCRResponse(
            raw_text=raw_text,
            pages=pages,
            tables_detected=tables_detected,
            languages=sorted(
                languages
            ),
            confidence=1.0,
        )

    # =====================================================
    # Image preparation
    # =====================================================

    def _prepare_images(
        self,
        *,
        content: bytes,
        mime_type: str,
    ) -> list[str]:

        if mime_type == "application/pdf":
            return self._pdf_to_images(
                content
            )

        return [
            self._image_to_data_url(
                content=content,
                mime_type=mime_type,
            )
        ]

    def _image_to_data_url(
        self,
        *,
        content: bytes,
        mime_type: str,
    ) -> str:

        encoded = base64.b64encode(
            content
        ).decode(
            "utf-8"
        )

        return (
            f"data:{mime_type};base64,"
            f"{encoded}"
        )

    def _pdf_to_images(
        self,
        content: bytes,
    ) -> list[str]:

        try:
            import pypdfium2 as pdfium

        except ImportError as exc:
            raise RuntimeError(
                "PDF OCR requires pypdfium2."
            ) from exc

        document = pdfium.PdfDocument(
            content
        )

        images: list[str] = []

        for page_index in range(
            len(document)
        ):
            page = document[
                page_index
            ]

            bitmap = page.render(
                scale=2,
            )

            pil_image = bitmap.to_pil()

            buffer = BytesIO()

            pil_image.save(
                buffer,
                format="PNG",
            )

            encoded = base64.b64encode(
                buffer.getvalue()
            ).decode(
                "utf-8"
            )

            images.append(
                "data:image/png;base64,"
                + encoded
            )

        return images

    # =====================================================
    # Response parsing
    # =====================================================

    @staticmethod
    def _parse_response(
        content: str,
    ) -> dict:

        try:
            data = json.loads(
                content
            )

        except json.JSONDecodeError:
            return {
                "text": content,
                "language": "",
                "has_table": False,
            }

        if not isinstance(
            data,
            dict,
        ):
            return {
                "text": content,
                "language": "",
                "has_table": False,
            }

        return data