"""Capture option lookups must stay at one concurrent round trip.

The document row, the OCR capture and the field's suggestion list are
independent reads. They must be dispatched together, and the number of
statements must not depend on the field or the query text.
"""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import app.services.document.document_capture_service as capture_module
from app.services.document.document_capture_service import DocumentCaptureService

ORG_ID = UUID("00000000-0000-0000-0000-0000000000aa")


class Builder:
    def __init__(self, executed, table_name):
        self.executed = executed
        self.table_name = table_name

    def select(self, *_args, **_kwargs): return self
    def eq(self, *_args, **_kwargs): return self
    def limit(self, *_args, **_kwargs): return self
    def order(self, *_args, **_kwargs): return self
    def ilike(self, *_args, **_kwargs): return self
    def or_(self, *_args, **_kwargs): return self

    def execute(self):  # pragma: no cover - execute is stubbed in the tests
        self.executed.append(self.table_name)
        return SimpleNamespace(data=[])


class Database:
    def __init__(self, executed):
        self.executed = executed

    def table(self, table_name):
        return Builder(self.executed, table_name)


def _service(executed, *, suggestion_rows=()):
    service = DocumentCaptureService.__new__(DocumentCaptureService)
    service.db = Database(executed)

    async def fake_execute(builder):
        executed.append(builder.table_name)
        if builder.table_name == "documents":
            return SimpleNamespace(
                data=[
                    {
                        "vendor_name": "Acme",
                        "document_number": "INV-1",
                        "capture_overrides": {},
                    }
                ]
            )
        if builder.table_name == "ocr_results":
            return SimpleNamespace(
                data=[{"key_value_pairs": {"invoice_number": "INV-9"}}]
            )
        return SimpleNamespace(data=list(suggestion_rows))

    return service, fake_execute


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "query", "expected_tables"),
    [
        ("vendor_name", "", ["documents", "ocr_results", "vendors"]),
        ("gl_account_name", "office", ["documents", "ocr_results", "chart_of_accounts"]),
        ("document_number", "", ["documents", "ocr_results", "purchase_orders"]),
        # A field without a lookup still reads only the document and its OCR.
        ("currency", "", ["documents", "ocr_results"]),
    ],
)
async def test_options_uses_one_round_trip(monkeypatch, field, query, expected_tables):
    executed: list[str] = []
    service, fake_execute = _service(executed)
    monkeypatch.setattr(capture_module, "execute", fake_execute)

    values = await service.options(
        org_id=ORG_ID,
        document_id=uuid4(),
        field=field,
        query=query,
    )

    if field == "document_number":
        # The OCR invoice number is the captured value for this field.
        assert values[0] == {"value": "INV-9", "label": "INV-9", "source": "captured"}
    if field == "vendor_name":
        assert {"value": "Acme", "label": "Acme", "source": "current"} in values
    assert sorted(executed) == sorted(expected_tables)


@pytest.mark.asyncio
async def test_options_keeps_url_encoded_apostrophes_in_search_text(monkeypatch):
    """Suggestion filters must still receive the caller's query verbatim."""
    executed: list[str] = []
    service, fake_execute = _service(
        executed, suggestion_rows=[{"id": str(uuid4()), "name": "O'Brien Ltd"}]
    )
    seen: list[str] = []

    class RecordingBuilder(Builder):
        def ilike(self, column, pattern):
            seen.append((column, pattern))
            return self

    service.db = SimpleNamespace(
        table=lambda name: RecordingBuilder(executed, name)
    )
    monkeypatch.setattr(capture_module, "execute", fake_execute)

    values = await service.options(
        org_id=ORG_ID,
        document_id=uuid4(),
        field="vendor_name",
        query="O'Brien",
    )

    assert ("name", "%O'Brien%") in seen
    assert {"value": "O'Brien Ltd", "label": "O'Brien Ltd", "source": "vendor", "id": values[-1]["id"]} in values
