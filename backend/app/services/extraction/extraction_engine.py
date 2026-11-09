from __future__ import annotations

import base64
import json
import logging
import re
from decimal import Decimal, InvalidOperation

from openai import AsyncOpenAI

from app.core.ai_config import EXTRACTION_MODEL
from app.core.config import settings
from app.models.invoice import INDUSTRY_LABELS, StructuredDocument

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)


class ExtractionEngine:
    """AI structured extraction with conservative financial normalization."""

    def build_prompt(self, industry: str) -> str:
        industry_label = INDUSTRY_LABELS.get(industry, "General")
        return f"""
You are an expert financial-document extraction engine for {industry_label} documents.

Return ONLY valid JSON with exactly these required top-level keys:
{{
  "document_type": "invoice | receipt | purchase_order | credit_note | debit_note | bank_statement | other | unknown",
  "sections": {{
    "document": {{
      "vendor_name": null,
      "document_number": null,
      "document_date": null,
      "due_date": null,
      "currency": null,
      "payment_terms": null,
      "payment_method": null
    }},
    "line_items": []
  }},
  "raw_totals": {{
    "subtotal": null,
    "tax_rate": null,
    "tax_amount": null,
    "discount_amount": null,
    "total_amount": null,
    "amount_paid": null,
    "amount_due": null
  }},
  "extraction_confidence": "high | medium | low"
}}

Financial accuracy rules:
- Never invent a value. If it is not visible in the supplied OCR text, return null.
- Preserve leading zeros in invoice/document numbers.
- Monetary values are numeric values without currency symbols.
- Currency MUST be returned as a 3-letter ISO 4217 code.
- Normalize symbols/codes: $ -> USD unless the document explicitly identifies another dollar currency; ₦ -> NGN; € -> EUR; £ -> GBP.
- Never leave currency null when a currency symbol/code/name is visible.
- A percentage must be represented as the visible percentage number in raw_totals.tax_rate (for example, visible "10%" -> 10). The application will normalize it to 0.10 for persistence. Never interpret 10% as a $10 tax.
- Extract tax rate and tax amount separately whenever the document shows them.
- If the document shows "Tax Rate: 10%" and "Tax: $35.00", return tax_rate=10 and tax_amount=35.
- Do not calculate a missing tax rate or tax amount merely from subtotal and total. Only extract values actually present in the OCR text.
- For every visible invoice/product/service row, preserve description, quantity, unit_price and amount.
- Do not silently drop rows.
- Do not round or alter values from the source.
""".strip()

    async def extract_from_text(self, raw_text: str, industry: str) -> StructuredDocument:
        if not raw_text.strip():
            raise ValueError("Cannot extract structured data from empty OCR text.")
        response = await client.chat.completions.create(
            model=EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": self.build_prompt(industry)},
                {"role": "user", "content": f"Extract all financial data from this OCR text.\n\n{raw_text}"},
            ],
            temperature=0,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return self._to_structured_document(content, industry, source_text=raw_text)

    async def extract_from_image(self, file_bytes: bytes, mime_type: str, industry: str) -> tuple[str, StructuredDocument]:
        if not file_bytes:
            raise ValueError("Cannot extract from an empty document.")
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")
        response = await client.chat.completions.create(
            model=EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": self.build_prompt(industry) + "\nAlso preserve all visible text exactly enough to audit the extracted financial fields."},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}", "detail": "high"}},
                    {"type": "text", "text": "Extract all data from this document."},
                ]},
            ],
            temperature=0,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        structured = self._to_structured_document(content, industry)
        return self._build_raw_text_summary(structured), structured

    def _to_structured_document(self, content: str, industry: str, source_text: str = "") -> StructuredDocument:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI structured extraction returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise ValueError("OpenAI structured extraction returned a non-object.")

        sections = data.get("sections")
        if not isinstance(sections, dict):
            sections = {}
        document = sections.get("document")
        if not isinstance(document, dict):
            document = {}
        line_items = sections.get("line_items")
        if not isinstance(line_items, list):
            line_items = []
        sections["document"] = document
        sections["line_items"] = line_items

        totals = data.get("raw_totals")
        if not isinstance(totals, dict):
            totals = {}
        totals = dict(totals)
        for key in ("subtotal", "tax_amount", "discount_amount", "total_amount", "amount_paid", "amount_due"):
            totals[key] = self._number(totals.get(key))
        totals["tax_rate"] = self._rate(totals.get("tax_rate"))

        # Recover explicitly labelled tax values from the OCR text when the
        # model omitted them. This is extraction, not calculation: both values
        # must be visibly labelled in the source text.
        if source_text:
            if totals.get("tax_rate") is None:
                match = re.search(r"(?:tax|vat|gst)[^\n]{0,40}?(?:rate|%)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*%", source_text, re.I)
                if match:
                    totals["tax_rate"] = self._rate(match.group(1))
            if totals.get("tax_amount") is None:
                match = re.search(r"(?:tax|vat|gst)(?:\s+amount)?\s*[:=]?\s*(?:[$€£₦]|USD|EUR|GBP|NGN)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", source_text, re.I)
                if match:
                    value = self._number(match.group(1))
                    if value is not None and value != totals.get("total_amount"):
                        totals["tax_amount"] = value

        # Currency is canonicalized here so the same value is used by the
        # persisted document, AP readiness checks, and the UI. The model may
        # return $, USD, US dollars, etc.; downstream code should not have to
        # interpret presentation symbols.
        currency = self._normalize_currency(
            document.get("currency"),
            source_text,
        )
        if currency:
            document["currency"] = currency
        elif source_text:
            inferred = self._infer_currency_from_text(source_text)
            if inferred:
                document["currency"] = inferred

        document_type = str(data.get("document_type") or "unknown").strip().lower()
        confidence = str(data.get("extraction_confidence") or "low").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"

        return StructuredDocument(
            industry=industry,
            document_type=document_type,
            sections=sections,
            raw_totals=totals,
            extraction_confidence=confidence,
        )

    @staticmethod
    def _number(value: object) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value).replace(",", "").replace("$", "").replace("€", "").replace("£", "").replace("₦", "").strip())
        except (InvalidOperation, TypeError, ValueError):
            return None

    @classmethod
    def _rate(cls, value: object) -> Decimal | None:
        number = cls._number(value)
        if number is None:
            return None
        if number > 1:
            number /= 100
        if number < 0 or number > 1:
            return None
        return number

    @classmethod
    def _normalize_currency(cls, value: object, source_text: str = "") -> str | None:
        if value is None:
            return cls._infer_currency_from_text(source_text)
        raw = str(value).strip().upper()
        if not raw:
            return cls._infer_currency_from_text(source_text)
        aliases = {
            "USD": "USD", "US$": "USD", "US DOLLAR": "USD", "US DOLLARS": "USD",
            "$": "USD", "NGN": "NGN", "N": "NGN", "₦": "NGN", "NAIRA": "NGN",
            "EUR": "EUR", "€": "EUR", "EURO": "EUR", "GBP": "GBP", "£": "GBP", "POUND": "GBP",
            "CAD": "CAD", "AUD": "AUD", "JPY": "JPY", "¥": "JPY", "CHF": "CHF",
        }
        if raw in aliases:
            return aliases[raw]
        match = re.search(r"\b([A-Z]{3})\b", raw)
        return match.group(1) if match else cls._infer_currency_from_text(source_text)

    @staticmethod
    def _infer_currency_from_text(source_text: str) -> str | None:
        text = source_text or ""
        upper = text.upper()
        if re.search(r"(?:\bNGN\b|\bNAIRA\b|₦)", text, re.I):
            return "NGN"
        if re.search(r"(?:\bEUR\b|\bEURO(?:S)?\b|€)", text, re.I):
            return "EUR"
        if re.search(r"(?:\bGBP\b|\bPOUND(?:S)?\b|£)", text, re.I):
            return "GBP"
        if re.search(r"(?:\bUSD\b|\bUS\s*DOLLAR(?:S)?\b|\bUSA\b|\bU\.S\.A?\.\b|\bUNITED STATES\b)", upper):
            return "USD"
        if "$" in text:
            # The canonical application mapping treats an unqualified dollar
            # sign as USD. Explicit NGN/EUR/GBP evidence above wins first.
            return "USD"
        return None

    @staticmethod
    def _build_raw_text_summary(doc: StructuredDocument) -> str:
        lines = [f"Document Type: {doc.document_type}"]
        document = doc.sections.get("document") or {}
        for key, value in document.items():
            if value is not None:
                lines.append(f"{key}: {value}")
        for index, item in enumerate(doc.sections.get("line_items") or [], 1):
            if isinstance(item, dict):
                lines.append("Row %s: %s" % (index, ", ".join(f"{k}: {v}" for k, v in item.items() if v is not None)))
        if doc.raw_totals:
            lines.append("[TOTALS]")
            for key, value in doc.raw_totals.items():
                if value is not None:
                    lines.append(f"{key}: {value}")
        return "\n".join(lines)
