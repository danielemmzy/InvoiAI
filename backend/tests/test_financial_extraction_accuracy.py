from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.extraction.extraction_engine import ExtractionEngine
from app.services.verification.math_check import MathCheck


def test_extraction_normalizes_percent_and_recovers_labeled_tax_values():
    engine = object.__new__(ExtractionEngine)
    structured = engine._to_structured_document(
        '{"document_type":"invoice","sections":{"document":{"vendor_name":"COMPANY"},"line_items":[{"description":"Product Description","quantity":1,"unit_price":50,"amount":50}]},"raw_totals":{"subtotal":350,"tax_rate":10,"tax_amount":null,"total_amount":385},"extraction_confidence":"high"}',
        "general",
        source_text="Subtotal $350.00\nTax Rate 10%\nTax $35.00\nTOTAL $385.00",
    )
    assert structured.document_type == "invoice"
    assert structured.raw_totals["subtotal"] == Decimal("350")
    assert structured.raw_totals["tax_rate"] == Decimal("0.1")
    assert structured.raw_totals["tax_amount"] == Decimal("35")
    assert structured.raw_totals["total_amount"] == Decimal("385")


@pytest.mark.asyncio
async def test_math_check_verifies_subtotal_tax_and_total():
    document = SimpleNamespace(
        subtotal=Decimal("350.00"), tax_rate=Decimal("0.10"), tax_amount=Decimal("35.00"),
        discount_amount=Decimal("0.00"), total_amount=Decimal("385.00"),
    )
    line_items = [
        {"description": "Product Description", "quantity": Decimal("1"), "unit_price": Decimal("50"), "amount": Decimal("50")}
        for _ in range(7)
    ]
    result = await MathCheck().run(document, line_items)
    assert result.passed is True
    assert result.score == 100
    assert result.metadata["expected_total"] == Decimal("385.00")
    assert result.metadata["actual_total"] == Decimal("385.00")
    assert result.metadata["variance"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_math_check_flags_missing_tax_when_total_exceeds_subtotal():
    document = SimpleNamespace(
        subtotal=Decimal("350.00"), tax_rate=None, tax_amount=None,
        discount_amount=Decimal("0.00"), total_amount=Decimal("385.00"),
    )
    line_items = [
        {"description": "Product Description", "quantity": Decimal("1"), "unit_price": Decimal("50"), "amount": Decimal("50")}
        for _ in range(7)
    ]
    result = await MathCheck().run(document, line_items)
    assert result.passed is False
    assert result.score < 100
    assert any("cannot be fully reconciled" in reason for reason in result.reasons)


def test_extraction_keeps_missing_tax_values_null():
    engine = object.__new__(ExtractionEngine)
    structured = engine._to_structured_document(
        '{"document_type":"invoice","sections":{"document":{},"line_items":[]},"raw_totals":{"subtotal":350,"tax_rate":null,"tax_amount":null,"discount_amount":null,"total_amount":350},"extraction_confidence":"high"}',
        "general",
        source_text="Subtotal: $350.00\nTax Rate: \nTax/VAT: \nDiscount: \nTotal/Grand Total: $350.00",
    )
    assert structured.raw_totals["subtotal"] == Decimal("350")
    assert structured.raw_totals["tax_rate"] is None
    assert structured.raw_totals["tax_amount"] is None
    assert structured.raw_totals["discount_amount"] is None
    assert structured.raw_totals["total_amount"] == Decimal("350")


@pytest.mark.asyncio
async def test_image_cross_check_reports_disagreement_without_replacing_ocr_values():
    from app.services.extraction.extraction_service import ExtractionService

    class FakeEngine:
        async def extract_from_image(self, *, file_bytes, mime_type, industry):
            return "image", type("Structured", (), {
                "raw_totals": {"subtotal": Decimal("350"), "tax_rate": Decimal("0.10"), "tax_amount": Decimal("35"), "discount_amount": None, "total_amount": Decimal("385")},
            })()

    service = ExtractionService(FakeEngine())
    ocr_structured = type("Structured", (), {
        "raw_totals": {"subtotal": Decimal("350"), "tax_rate": None, "tax_amount": None, "discount_amount": None, "total_amount": Decimal("350")},
    })()

    warnings = await service.compare_ocr_to_image(
        file_bytes=b"image",
        mime_type="image/webp",
        industry="general",
        structured_from_ocr=ocr_structured,
    )

    assert any("OCR/image disagreement for tax rate" in warning for warning in warnings)
    assert any("OCR/image disagreement for tax amount" in warning for warning in warnings)


def test_document_domain_allows_missing_currency_and_paid_amount():
    from uuid import uuid4
    from app.core.enum.database import DocumentSource, DocumentType, FileType, DocumentStatus, PipelineStage
    from app.models.domain.document import Document

    document = Document(
        id=uuid4(),
        org_id=uuid4(),
        source=DocumentSource.MANUAL,
        document_type=DocumentType.INVOICE,
        industry="general",
        file_url="https://example.test/document.png",
        file_name="document.png",
        file_type=FileType.PNG,
        currency=None,
        paid_amount=None,
        pipeline_stage=PipelineStage.OCR,
        status=DocumentStatus.PENDING,
    )

    assert document.currency is None
    assert document.paid_amount is None


def test_invoice_rule_classification_is_deterministic():
    from app.services.document.classifier_service import _rule_classify

    result = _rule_classify(
        "INVOICE\nInvoice No: 0123456789\nSubtotal: $350.00\nTOTAL: $385.00",
        "OIP (1).webp",
    )

    assert result is not None
    assert result["document_type"] == "invoice"
    assert result["source"] == "rules"

@pytest.mark.asyncio
async def test_missing_vendor_is_unavailable_not_zero_fraud_risk():
    from app.services.verification.fraud_check import FraudCheck
    from app.services.verification.vendor_check import VendorCheck

    document = SimpleNamespace(id="document-1", total_amount=Decimal("2338.35"))

    vendor_result = await VendorCheck().run(document, None)
    fraud_result = await FraudCheck().run(document, None)

    assert vendor_result.metadata["available"] is False
    assert fraud_result.metadata["available"] is False
    assert vendor_result.confidence == 0
    assert fraud_result.confidence == 0
    assert "could not be resolved" in vendor_result.reasons[0].lower()
    assert "could not be resolved" in fraud_result.reasons[0].lower()

@pytest.mark.asyncio
async def test_verification_engine_does_not_treat_unavailable_vendor_as_zero_score():
    from app.services.verification.engine import VerificationEngine
    from app.services.verification.result import VerificationResult

    def result(score: int, available: bool = True):
        return VerificationResult(
            passed=available,
            score=score,
            confidence=100 if available else 0,
            summary="test",
            metadata={"available": available},
        )

    class Module:
        def __init__(self, value):
            self.value = value
        async def run(self, *args, **kwargs):
            return self.value

    engine = VerificationEngine(
        Module(result(100)),
        Module(result(100)),
        Module(result(0, False)),
        Module(result(100)),
        Module(result(100)),
        Module(result(90)),
        Module(result(0, False)),
        Module(result(100)),
    )

    verification = await engine.verify(
        document=SimpleNamespace(id="document-1", purchase_order_id=None),
        ocr=SimpleNamespace(),
        line_items=[],
        vendor=None,
        purchase_order=None,
        duplicate_document=None,
    )

    assert verification["overall_score"] == 98
    assert verification["unavailable_modules"] == ["vendor", "fraud"]
