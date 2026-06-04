import json
import base64
import logging
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.invoice import StructuredDocument, INDUSTRY_LABELS

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)

# ── Prompt builder ─────────────────────────────────────────────────────────────
# Industry is injected as context — it guides GPT's understanding
# without constraining the output shape.
# GPT knows what auditing documents look like vs ecommerce invoices.
# We let it decide the sections and fields, we just tell it the domain.
# ──────────────────────────────────────────────────────────────────────────────

def build_prompt(industry: str) -> str:
    industry_label = INDUSTRY_LABELS.get(industry, "General")

    return f"""
You are an expert document extraction engine specialized in {industry_label} documents.

Your job:
1. Detect the exact document type (Invoice, Receipt, Audit Report, Tax Return, Purchase Order, etc.)
2. Identify EVERY table, section, and data group present in the document
3. Extract ALL fields exactly as they appear — do not skip anything
4. Structure them logically into named sections
5. Rate your own confidence in the extraction

Return ONLY valid JSON. No markdown. No explanation. No code blocks.

JSON structure:
{{
  "document_type": "exact document type detected",
  "sections": {{
    "section_name_snake_case": {{
      "field_name": "value"
    }},
    "section_with_rows": [
      {{"field": "value"}}
    ]
  }},
  "raw_totals": {{
    "any_monetary_total_name": numeric_value
  }},
  "extraction_confidence": "high | medium | low"
}}

Rules:
- Section names must be snake_case (e.g. line_items, engagement_details, tax_summary)
- Sections with multiple rows (line items, findings, transactions) must be arrays of objects
- Single-record sections (header info, totals, parties) must be plain objects
- All monetary values as plain floats — no currency symbols
- Dates as strings in their original format
- Numbers as floats or integers — never strings
- If a field is empty or not found return null for that field
- raw_totals must include every monetary total you can find in the document
- Never invent or assume fields that are not present in the document
- For {industry_label} documents specifically, pay close attention to
  industry-standard fields and terminology common in this domain
""".strip()


# ── Text extraction (digital PDFs) ────────────────────────────────────────────

async def extract_from_text(raw_text: str, industry: str) -> StructuredDocument:
    """
    Sends raw text (from pdfplumber) to GPT-4o-mini for structuring.

    Why 4o-mini for text?
    - Text is already clean — no visual interpretation needed
    - 4o-mini is 10x cheaper than 4o and handles structured extraction perfectly
    - temperature=0 gives deterministic output — same invoice always gives same result
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": build_prompt(industry)
                },
                {
                    "role": "user",
                    "content": f"Extract all data from this document:\n\n{raw_text}"
                }
            ],
            temperature=0,
            max_tokens=3000,        # increased from 1500 — complex docs need more
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        return StructuredDocument(
            industry=industry,
            document_type=data.get("document_type", "Unknown"),
            sections=data.get("sections", {}),
            raw_totals=data.get("raw_totals", {}),
            extraction_confidence=data.get("extraction_confidence", "medium"),
        )

    except json.JSONDecodeError as e:
        logger.error(f"GPT-4o-mini returned invalid JSON: {e}")
        return _empty_document(industry)

    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        return _empty_document(industry)


# ── Image / scanned PDF extraction ────────────────────────────────────────────

async def extract_from_image(
    file_bytes: bytes,
    mime_type: str,
    industry: str
) -> tuple[str, StructuredDocument]:
    """
    Sends image bytes to GPT-4o Vision.
    One call: sees the image, extracts text, structures data.
    Returns (raw_text_summary, StructuredDocument).

    Why 4o for images?
    - Vision capability requires gpt-4o, not available in mini
    - detail: "high" is important — invoice text is small and dense
    """
    try:
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": build_prompt(industry)
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all data from this document image."
                        }
                    ]
                }
            ],
            temperature=0,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        structured = StructuredDocument(
            industry=industry,
            document_type=data.get("document_type", "Unknown"),
            sections=data.get("sections", {}),
            raw_totals=data.get("raw_totals", {}),
            extraction_confidence=data.get("extraction_confidence", "medium"),
        )

        # Build plain text summary for raw_text storage and search
        raw_text = _build_raw_text_summary(structured)

        return raw_text, structured

    except json.JSONDecodeError as e:
        logger.error(f"GPT-4o Vision returned invalid JSON: {e}")
        return "", _empty_document(industry)

    except Exception as e:
        logger.error(f"Vision extraction failed: {e}")
        return "", _empty_document(industry)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty_document(industry: str) -> StructuredDocument:
    """Returns a safe empty document when extraction fails."""
    return StructuredDocument(
        industry=industry,
        document_type="Unknown",
        sections={},
        raw_totals={},
        extraction_confidence="low",
    )


def _build_raw_text_summary(doc: StructuredDocument) -> str:
    """
    Flattens a StructuredDocument into a plain text string.
    Used for raw_text storage — useful for search and debugging.
    Not shown to users.
    """
    lines = [
        f"Document Type: {doc.document_type}",
        f"Industry: {doc.industry}",
    ]

    for section_name, section_data in doc.sections.items():
        lines.append(f"\n[{section_name.upper().replace('_', ' ')}]")

        if isinstance(section_data, list):
            for i, row in enumerate(section_data, 1):
                if isinstance(row, dict):
                    lines.append(f"  Row {i}: " + ", ".join(
                        f"{k}: {v}" for k, v in row.items() if v is not None
                    ))
        elif isinstance(section_data, dict):
            for key, value in section_data.items():
                if value is not None:
                    lines.append(f"  {key}: {value}")

    if doc.raw_totals:
        lines.append("\n[TOTALS]")
        for key, value in doc.raw_totals.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)