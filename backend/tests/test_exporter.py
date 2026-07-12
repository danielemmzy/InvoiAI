from io import BytesIO

from openpyxl import load_workbook
from openpyxl import Workbook

from app.models.invoice import StructuredDocument
from app.services.exporter import (
    export_to_excel,
    export_to_csv,
    _ordered_keys,
    _label,
    _build_table_sheet,
    _build_keyvalue_sheet,
)


def sample_doc():
    return StructuredDocument(
        industry="general",
        document_type="Invoice",
        extraction_confidence="high",
        raw_totals={
            "subtotal": 100,
            "tax": 10,
            "total": 110,
        },
        sections={
            "header": {
                "invoice_number": "INV001",
                "vendor": "OpenAI",
            },
            "line_items": [
                {
                    "description": "Laptop",
                    "quantity": 2,
                    "unit_price": 500,
                }
            ],
        },
    )


def test_export_excel():
    data = export_to_excel(sample_doc())

    wb = load_workbook(BytesIO(data))

    assert "Summary" in wb.sheetnames
    assert "Header" in wb.sheetnames
    assert "Line Items" in wb.sheetnames


def test_export_csv():
    csv_bytes = export_to_csv(sample_doc())

    text = csv_bytes.decode()

    assert "Invoice" in text
    assert "OpenAI" in text
    assert "Laptop" in text
    assert "Subtotal" in text


def test_ordered_keys():
    rows = [
        {
            "amount": 100,
            "description": "A",
            "zzz": 1,
            "quantity": 2,
        }
    ]

    keys = _ordered_keys(rows)

    assert keys == [
        "description",
        "quantity",
        "amount",
        "zzz",
    ]


def test_label():
    assert _label("invoice_number") == "Invoice Number"


def test_build_table_sheet_empty():
    wb = Workbook()

    _build_table_sheet(
        wb,
        "Items",
        [],
    )

    assert "Items" in wb.sheetnames


def test_build_keyvalue_nested():
    wb = Workbook()

    _build_keyvalue_sheet(
        wb,
        "Header",
        {
            "vendor": {
                "name": "OpenAI",
                "country": "USA",
            }
        },
    )

    ws = wb["Header"]

    assert ws["A2"].value == "Vendor"


def test_build_keyvalue_list():
    wb = Workbook()

    _build_keyvalue_sheet(
        wb,
        "Tags",
        {
            "tags": ["A", "B", "C"]
        },
    )

    ws = wb["Tags"]

    assert ws["B2"].value == "A, B, C"


def test_build_keyvalue_none():
    wb = Workbook()

    _build_keyvalue_sheet(
        wb,
        "Header",
        {
            "vendor": None
        },
    )

    ws = wb["Header"]

    assert ws["B2"].value == ""