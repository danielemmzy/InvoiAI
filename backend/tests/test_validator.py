from app.models.invoice import StructuredDocument
from app.services.validator import validate_document, _check_totals, _find


def make_doc(
    sections=None,
    confidence="high",
    document_type="Invoice",
    totals=None,
):
    return StructuredDocument(
        industry="general",
        document_type=document_type,
        sections=sections or {},
        raw_totals=totals or {},
        extraction_confidence=confidence,
    )


def test_blank_document():
    doc = make_doc(sections={})

    warnings = validate_document(doc)

    assert len(warnings) == 1
    assert "No data could be extracted" in warnings[0]


def test_low_confidence_warning():
    doc = make_doc(
        sections={"header": {"invoice": "123"}},
        confidence="low",
    )

    warnings = validate_document(doc)

    assert any("Low extraction confidence" in w for w in warnings)


def test_unknown_document_type():
    doc = make_doc(
        sections={"header": {"invoice": "123"}},
        document_type="Unknown",
    )

    warnings = validate_document(doc)

    assert any("Document type could not be identified" in w for w in warnings)


def test_empty_sections_warning():
    doc = make_doc(
        sections={
            "header": {"invoice": "123"},
            "items": [],
            "totals": {},
        }
    )

    warnings = validate_document(doc)

    assert any("Empty sections detected" in w for w in warnings)


def test_totals_match():
    totals = {
        "subtotal": 100,
        "tax": 10,
        "total": 110,
    }

    warnings = _check_totals(totals)

    assert warnings == []


def test_totals_mismatch():
    totals = {
        "subtotal": 100,
        "tax": 10,
        "total": 150,
    }

    warnings = _check_totals(totals)

    assert len(warnings) == 1
    assert "Totals mismatch" in warnings[0]


def test_totals_with_shipping():
    totals = {
        "subtotal": 100,
        "tax": 10,
        "shipping": 20,
        "total": 130,
    }

    warnings = _check_totals(totals)

    assert warnings == []


def test_totals_not_enough_fields():
    warnings = _check_totals({"total": 100})

    assert warnings == []


def test_find_returns_value():
    totals = {
        "grand_total": 500
    }

    assert _find(
        totals,
        ["total", "grand_total"]
    ) == 500


def test_find_returns_none():
    assert _find({}, ["total"]) is None