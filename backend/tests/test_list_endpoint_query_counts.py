"""Query-count guards for list endpoints that already join in the database.

The purchase-order list and the goods-receipt list must stay at one statement
per request: related rows are embedded by PostgREST, never fetched per row.
"""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.repositories.document.purchase_order_repository import PurchaseOrderRepository

ORG_ID = UUID("00000000-0000-0000-0000-0000000000aa")


class RecordingQuery:
    def __init__(self, executed, table_name, rows):
        self.executed = executed
        self.table_name = table_name
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def ilike(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def execute(self):
        self.executed.append(self.table_name)
        return SimpleNamespace(data=self.rows(), count=len(self.rows()))


class RecordingDatabase:
    def __init__(self, rows_for):
        self.executed = []
        self.rows_for = rows_for

    def table(self, table_name):
        return RecordingQuery(self.executed, table_name, lambda: self.rows_for(table_name))


@pytest.mark.asyncio
async def test_purchase_order_list_embeds_vendors_in_one_statement():
    database = RecordingDatabase(
        lambda table: (
            [
                {
                    "id": str(uuid4()),
                    "po_number": "PO-1",
                    "vendor_id": str(uuid4()),
                    "amount": "100.00",
                    "matched_amount": "0",
                    "vendors": {"name": "Supplier"},
                }
                for _ in range(10)
            ]
            if table == "purchase_orders"
            else []
        )
    )
    repository = object.__new__(PurchaseOrderRepository)
    repository.db = database

    rows, total = await repository.list_purchase_orders(ORG_ID, limit=10)

    assert total == 10
    assert len(rows) == 10
    assert database.executed == ["purchase_orders"]


@pytest.mark.asyncio
async def test_goods_receipt_list_embeds_lines_in_one_statement(monkeypatch):
    import app.routers.goods_receipts as goods_receipts_router

    database = RecordingDatabase(
        lambda table: (
            [{"id": str(uuid4()), "goods_receipt_lines": [{"id": str(uuid4())}]}]
            if table == "goods_receipts"
            else []
        )
    )
    monkeypatch.setattr(goods_receipts_router, "get_supabase", lambda: database)

    receipts = await goods_receipts_router.list_receipts(
        uuid4(),
        ctx=SimpleNamespace(org_id=ORG_ID),
        _=None,
    )

    assert len(receipts) == 1
    assert database.executed == ["goods_receipts"]


@pytest.mark.asyncio
async def test_ap_exceptions_fetch_documents_in_one_statement(monkeypatch):
    import app.routers.ap as ap_router

    executed = []
    document_ids = [str(uuid4()) for _ in range(5)]

    class ExceptionRow:
        def __init__(self, document_id):
            self.document_id = document_id

        def model_dump(self, **_kwargs):
            return {"document_id": self.document_id}

    class Exceptions:
        async def list_open(self, _org_id):
            return [ExceptionRow(document_id) for document_id in document_ids]

    class DocumentsQuery:
        def select(self, *_args, **_kwargs): return self
        def eq(self, *_args, **_kwargs): return self

        def in_(self, _column, values):
            self.values = list(values)
            return self

        def execute(self):
            executed.append(list(self.values))
            return SimpleNamespace(
                data=[
                    {"id": document_id, "document_number": "INV-1"}
                    for document_id in self.values
                ]
            )

    monkeypatch.setattr(ap_router, "ExceptionService", lambda: Exceptions())
    monkeypatch.setattr(
        ap_router,
        "db",
        lambda: SimpleNamespace(table=lambda _name: DocumentsQuery()),
    )

    rows = await ap_router.list_exceptions(ctx=SimpleNamespace(org_id=ORG_ID), _=None)

    assert sorted(row["document"]["id"] for row in rows) == sorted(document_ids)
    # One lookup for every exception's document, never one per exception.
    assert len(executed) == 1
    assert sorted(executed[0]) == sorted(document_ids)
