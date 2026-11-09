from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.enum.database import DocumentType

log = logging.getLogger(__name__)

PROMPT = (
    "Classify this document. Return JSON only: "
    "{document_type,confidence,reason}. "
    "document_type must be one of invoice,receipt,purchase_order,quotation,"
    "contract,bank_statement,credit_note,debit_note,expense_report,delivery_note,"
    "payslip,tax_document,audit_report,financial_statement,csv_export,spreadsheet,unknown. "
    "Never invent."
)

KEYWORDS = {
    DocumentType.INVOICE: ("invoice", "amount due", "invoice number"),
    DocumentType.RECEIPT: ("receipt", "total paid", "cashier"),
    DocumentType.PURCHASE_ORDER: ("purchase order", "po number"),
    DocumentType.BANK_STATEMENT: ("bank statement", "account statement", "opening balance", "closing balance", "transaction date"),
    DocumentType.QUOTATION: ("quotation", "quote", "estimate"),
    DocumentType.CONTRACT: ("agreement", "contract", "terms and conditions"),
    DocumentType.CREDIT_NOTE: ("credit note", "credit memo"),
    DocumentType.DEBIT_NOTE: ("debit note", "debit memo"),
    DocumentType.DELIVERY_NOTE: ("delivery note", "goods received"),
    DocumentType.EXPENSE_REPORT: ("expense report", "expense claim"),
    DocumentType.PAYSLIP: ("payslip", "net pay", "gross pay"),
    DocumentType.TAX_DOCUMENT: ("tax return", "tax certificate"),
    DocumentType.FINANCIAL_STATEMENT: ("balance sheet", "income statement", "cash flow statement"),
}


def _rule_classify(text: str, filename: str) -> dict[str, Any] | None:
    """Classify obvious document types without calling an AI model.

    This is intentionally safe for the upload/intake path: it uses strong
    filename and lexical signals only.  In particular, PO numbers such as
    ``PO-0034`` must not be mistaken for invoices merely because an invoice
    extraction field later happens to contain a document number.
    """
    filename_text = (filename or "").lower()
    body_text = (text or "").lower()
    haystack = f"{filename_text} {body_text}"

    strong_patterns = (
        (
            DocumentType.PURCHASE_ORDER,
            (
                r"purchase[ _-]*order",
                r"\bpo[ _#.:/-]*\d+\b",
                r"\bp\.?o\.?[ _#.:/-]*\d+\b",
                r"\bpurchase[ _-]*order[ _-]*(?:no|number|#)\b",
            ),
        ),
        (
            DocumentType.RECEIPT,
            (
                r"\breceipt\b",
                r"total[ _-]+paid",
                r"payment[ _-]+received",
            ),
        ),
        (
            DocumentType.INVOICE,
            (
                r"\binvoice\b",
                r"invoice[ _-]*(?:no|number|#)\b",
                r"amount[ _-]+due",
            ),
        ),
    )

    # Strong PO/receipt/invoice markers win before generic keyword scoring.
    # This prevents ``PO-0034`` + financial totals from being labeled invoice.
    for dtype, patterns in strong_patterns:
        if any(re.search(pattern, haystack, flags=re.IGNORECASE) for pattern in patterns):
            return {
                "document_type": dtype.value,
                "confidence": 0.97 if dtype == DocumentType.PURCHASE_ORDER else 0.94,
                "reason": f"Detected strong {dtype.value.replace('_', ' ')} document signals.",
                "source": "rules",
            }

    scores = {kind: sum(signal in haystack for signal in signals) for kind, signals in KEYWORDS.items()}
    dtype, score = max(scores.items(), key=lambda item: item[1])
    if score <= 0:
        return None
    return {
        "document_type": dtype.value,
        "confidence": min(0.95, 0.55 + 0.08 * score),
        "reason": f"Matched {score} document signal(s).",
        "source": "rules",
    }


class DocumentClassifierService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def classify_rules(self, text: str, filename: str = "") -> dict[str, Any] | None:
        """Return a deterministic classification when the document text is explicit."""
        return _rule_classify((text or "")[:30000], filename)

    async def classify(self, text: str, filename: str = "") -> dict[str, Any]:
        text = (text or "")[:30000]

        # Classification should be cheap and deterministic when the OCR text
        # contains an explicit document signal. This avoids an unnecessary
        # second OpenAI request for obvious invoices/receipts/etc.
        rule_result = self.classify_rules(text, filename)
        if rule_result is not None:
            return rule_result

        if self.client and text:
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": PROMPT},
                        {"role": "user", "content": f"Filename: {filename}\n{text}"},
                    ],
                    timeout=12,
                    max_retries=0,
                )
                payload = json.loads(response.choices[0].message.content or "{}")
                detected = str(payload.get("document_type", "unknown"))
                try:
                    detected = DocumentType(detected).value
                except ValueError:
                    detected = "unknown"

                # Never allow an unreliable AI `unknown` to override a clear
                # lexical signal if one became available in the same text.
                if detected == DocumentType.UNKNOWN.value:
                    fallback = self.classify_rules(text, filename)
                    if fallback is not None:
                        return fallback

                return {
                    "document_type": detected,
                    "confidence": max(0, min(1, float(payload.get("confidence", 0)))),
                    "reason": str(payload.get("reason", "AI classification"))[:500],
                    "source": "ai",
                }
            except Exception:
                log.exception("classifier fallback")

        return {
            "document_type": DocumentType.UNKNOWN.value,
            "confidence": 0.2,
            "reason": "No reliable document signals detected.",
            "source": "rules",
        }
