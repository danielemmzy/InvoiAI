"""Query-count regression tests for AP GL coding batching.

These guard the two historical N+1 sites: persisting one coding per line, and
re-reading this vendor's coding history for every line.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.enum.ap import APCodingStatus
from app.models.domain.ap import InvoiceCoding
from app.repositories.ap.coding_repository import InvoiceCodingRepository
from app.services.ap.gl_coding_service import GLCodingService


class CountingQuery:
    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name
        self.operation = "select"
        self.payload = None
        self.filters = []
        self.wanted_ids = None

    def select(self, *_args, **_kwargs):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def neq(self, *_args, **_kwargs):
        return self

    def in_(self, column, values):
        self.wanted_ids = (column, {str(value) for value in values})
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        self.database.executed.append((self.table_name, self.operation))
        if self.operation == "insert":
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            now = datetime.now(UTC).isoformat()
            return SimpleNamespace(
                data=[
                    {**row, "id": str(uuid4()), "created_at": now, "updated_at": now}
                    for row in rows
                ]
            )
        if self.operation == "update":
            return SimpleNamespace(data=[{**(self.payload or {}), "id": "updated"}])
        return SimpleNamespace(data=self.database.rows_for(self.table_name, self.wanted_ids))


class CountingDatabase:
    def __init__(self):
        self.executed = []
        self.documents = [{"id": str(uuid4())} for _ in range(3)]
        self.line_item_count = 0

    def table(self, name):
        return CountingQuery(self, name)

    def rows_for(self, table_name, wanted_ids):
        if table_name == "documents":
            return self.documents
        if table_name == "document_line_items":
            ids = {row["id"] for row in self.documents} if wanted_ids is None else wanted_ids[1]
            return [
                {
                    "id": str(uuid4()),
                    "document_id": document_id,
                    "description": "Cloud subscription",
                }
                for document_id in sorted(ids)
                for _ in range(max(1, self.line_item_count))
            ]
        if table_name == "invoice_codings":
            return []
        raise AssertionError(f"Unexpected table queried: {table_name}")


def _coding(document_id, line_item_id):
    now = datetime.now(UTC)
    return InvoiceCoding(
        id=uuid4(),
        org_id=uuid4(),
        document_id=document_id,
        line_item_id=line_item_id,
        gl_account_id=uuid4(),
        confidence=95,
        status=APCodingStatus.AUTO_CODED,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_save_codings_uses_one_read_and_one_insert_for_all_lines():
    document_id = uuid4()
    codings = [_coding(document_id, uuid4()) for _ in range(25)]
    database = CountingDatabase()
    repository = object.__new__(InvoiceCodingRepository)
    repository.table = lambda: database.table("invoice_codings")

    saved = await repository.save_codings(codings)

    assert len(saved) == 25
    assert database.executed == [
        ("invoice_codings", "select"),
        ("invoice_codings", "insert"),
    ]


@pytest.mark.asyncio
async def test_coding_history_is_loaded_once_regardless_of_line_count():
    database = CountingDatabase()
    service = GLCodingService.__new__(GLCodingService)
    service.codings = SimpleNamespace(db=database)
    org_id, document_id, vendor_id = uuid4(), uuid4(), uuid4()

    for line_count in (1, 10):
        database.executed.clear()
        database.line_item_count = line_count
        history = await service._load_history(
            org_id,
            document_id,
            vendor_id,
            [{"id": uuid4(), "description": f"line {index}"} for index in range(line_count)],
        )
        assert history is not None
        # The history page query runs first; the two follow-up reads are
        # dispatched with asyncio.gather, so their completion order is not
        # deterministic. Assert the exact multiset, not a fixed order.
        assert database.executed[0] == ("documents", "select")
        assert sorted(database.executed[1:]) == [
            ("document_line_items", "select"),
            ("invoice_codings", "select"),
        ]
        assert len(database.executed) == 3


@pytest.mark.asyncio
async def test_code_line_does_not_query_when_history_is_prefetched():
    class ExplodingDatabase:
        def table(self, name):  # pragma: no cover - failure path
            raise AssertionError(f"Unexpected history query for {name}")

    service = GLCodingService.__new__(GLCodingService)
    service.codings = SimpleNamespace(db=ExplodingDatabase())
    service.rules = SimpleNamespace(increment_match_count=lambda *_: None)

    class AsyncNoop:
        async def __call__(self, *_args, **_kwargs):
            return None

    service.rules = SimpleNamespace(increment_match_count=AsyncNoop())

    history = {"doc_ids": [], "items_by_doc": {}, "coding_by_item": {}}
    coding = await service._code_line(
        uuid4(),
        uuid4(),
        {"id": uuid4(), "description": "no rule matches this"},
        uuid4(),
        [],
        [],
        history,
    )

    assert coding.status == APCodingStatus.NEEDS_REVIEW
