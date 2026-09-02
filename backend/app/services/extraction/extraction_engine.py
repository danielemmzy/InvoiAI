"""
============================================================
Extraction Engine

Responsible for AI-powered document extraction.

Responsibilities
----------------
- Build prompts
- Call OpenAI
- Structure extracted data
- Return StructuredDocument

No repositories.
No business logic.
No persistence.
============================================================
"""

from __future__ import annotations

import base64
import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.invoice import (
    INDUSTRY_LABELS,
    StructuredDocument,
)

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
)


class ExtractionEngine:
    """
    AI extraction engine.
    """

    # ==========================================================
    # Prompt
    # ==========================================================

    def build_prompt(
        self,
        industry: str,
    ) -> str:

        industry_label = INDUSTRY_LABELS.get(
            industry,
            "General",
        )

        return f"""
You are an expert document extraction engine specialized in {industry_label} documents.

Your job:
1. Detect the exact document type
2. Identify EVERY table, section, and data group
3. Extract ALL fields
4. Structure them logically
5. Rate extraction confidence

Return ONLY valid JSON.

JSON structure:
{{
  "document_type": "...",
  "sections": {{}},
  "raw_totals": {{}},
  "extraction_confidence": "high | medium | low"
}}

Rules:

- Never invent values.
- Monetary values are floats.
- Dates remain strings.
- Missing fields become null.
""".strip()

    # ==========================================================
    # Text Extraction
    # ==========================================================

    async def extract_from_text(
        self,
        raw_text: str,
        industry: str,
    ) -> StructuredDocument:

        try:

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self.build_prompt(
                            industry,
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Extract all data from:\n\n{raw_text}"
                        ),
                    },
                ],
                temperature=0,
                max_tokens=3000,
                response_format={
                    "type": "json_object",
                },
            )

            content = response.choices[0].message.content

            data = json.loads(content)

            return StructuredDocument(
                industry=industry,
                document_type=data.get(
                    "document_type",
                    "Unknown",
                ),
                sections=data.get(
                    "sections",
                    {},
                ),
                raw_totals=data.get(
                    "raw_totals",
                    {},
                ),
                extraction_confidence=data.get(
                    "extraction_confidence",
                    "medium",
                ),
            )

        except Exception as e:

            logger.exception(e)

            return self._empty_document(
                industry,
            )

    # ==========================================================
    # Image Extraction
    # ==========================================================

    async def extract_from_image(
        self,
        file_bytes: bytes,
        mime_type: str,
        industry: str,
    ) -> tuple[str, StructuredDocument]:

        try:

            image_b64 = base64.b64encode(
                file_bytes,
            ).decode()

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": self.build_prompt(
                            industry,
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}",
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "text",
                                "text": "Extract all data from this document.",
                            },
                        ],
                    },
                ],
                temperature=0,
                max_tokens=3000,
                response_format={
                    "type": "json_object",
                },
            )

            content = response.choices[0].message.content

            data = json.loads(content)

            structured = StructuredDocument(
                industry=industry,
                document_type=data.get(
                    "document_type",
                    "Unknown",
                ),
                sections=data.get(
                    "sections",
                    {},
                ),
                raw_totals=data.get(
                    "raw_totals",
                    {},
                ),
                extraction_confidence=data.get(
                    "extraction_confidence",
                    "medium",
                ),
            )

            raw_text = self._build_raw_text_summary(
                structured,
            )

            return raw_text, structured

        except Exception as e:

            logger.exception(e)

            return (
                "",
                self._empty_document(
                    industry,
                ),
            )

    # ==========================================================
    # Helpers
    # ==========================================================

    def _empty_document(
        self,
        industry: str,
    ) -> StructuredDocument:

        return StructuredDocument(
            industry=industry,
            document_type="Unknown",
            sections={},
            raw_totals={},
            extraction_confidence="low",
        )

    def _build_raw_text_summary(
        self,
        doc: StructuredDocument,
    ) -> str:

        lines = [
            f"Document Type: {doc.document_type}",
            f"Industry: {doc.industry}",
        ]

        for section_name, section_data in doc.sections.items():

            lines.append(
                f"\n[{section_name.upper().replace('_', ' ')}]"
            )

            if isinstance(section_data, list):

                for i, row in enumerate(section_data, 1):

                    if isinstance(row, dict):

                        lines.append(
                            f"Row {i}: "
                            + ", ".join(
                                f"{k}: {v}"
                                for k, v in row.items()
                                if v is not None
                            )
                        )

            elif isinstance(section_data, dict):

                for key, value in section_data.items():

                    if value is not None:

                        lines.append(
                            f"{key}: {value}"
                        )

        if doc.raw_totals:

            lines.append("\n[TOTALS]")

            for key, value in doc.raw_totals.items():

                lines.append(
                    f"{key}: {value}"
                )

        return "\n".join(lines)