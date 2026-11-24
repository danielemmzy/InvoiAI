"""Query-count regression tests for the payment authorization queue.

The queue is a list page: its cost must not grow with the number of
payment-ready documents. Previously it ran a lookup per row and a full
evaluation (several more queries) for every row without a stored decision.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.enum.ap import InvoiceAPStatus, PaymentAuthorizationStatus
from app.services.payment.payment_authorization_service import (
    PaymentAuthorizationService,
)


class Query:
    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name

    def select(self, *_args, **_kwargs): return self
    def eq(self, *_args, **_kwargs): return self
    def in_(self, *_args, **_kwargs): return self
    def order(self, *_args, **_kwargs): return self
    def limit(self, *_args, **_kwargs): return self

    def execute(self):
        self.database.executed.append(self.table_name)
        return SimpleNamespace(data=self.database.rows_for(self.table_name))


class Database:
    def __init__(self, document_count: int):
        self.executed = []
        self.document_count = document_count
        self.documents = [
            {
                "id": str(uuid4()),
                "vendor_id": str(uuid4()),
                "vendor_name": "Supplier",
                "total_amount": "100.00",
                "currency": "GBP",
                "document_number": f"INV-{index}",
                "due_date": "2026-11-20",
                "ap_status": InvoiceAPStatus.PAYMENT_READY.value,
                "erp_bill_id": None,
            }
            for index in range(document_count)
        ]

    def table(self, name):
        return Query(self, name)

    def rows_for(self, table_name):
        if table_name == "documents":
            return self.documents
        if table_name == "vendors":
            return []
        if table_name == "invoice_exceptions":
            return []
        raise AssertionError(f"Unexpected table queried: {table_name}")


class Repository:
    def __init__(self, database, *, has_authorizations: bool):
        self.database = database
        self.has_authorizations = has_authorizations
        self.calls: list[str] = []
        self.upserted: list[tuple[str, dict]] = []

    async def list_by_documents(self, org_id, document_ids):
        self.calls.append("list_by_documents")
        if not self.has_authorizations:
            return []
        return [
            SimpleNamespace(
                document_id=row["id"],
                status=PaymentAuthorizationStatus.AUTHORIZED.value,
                blocked_reasons=[],
            )
            for row in self.database.documents
            if row["id"] in set(document_ids)
        ]

    async def upsert_many(self, org_id, items):
        self.calls.append("upsert_many")
        self.upserted = items
        return [
            SimpleNamespace(
                document_id=document_id,
                status=payload["status"],
                blocked_reasons=payload["blocked_reasons"],
            )
            for document_id, payload in items
        ]

    async def upsert(self, *_args, **_kwargs):  # pragma: no cover - fallback path
        raise AssertionError("single-document upsert should not be used")


@pytest.mark.parametrize("document_count", [1, 40])
@pytest.mark.asyncio
async def test_queue_with_stored_authorizations_uses_two_queries(document_count):
    database = Database(document_count)
    repository = Repository(database, has_authorizations=True)
    service = PaymentAuthorizationService(
        db=database,
        repository=repository,
        vendors=SimpleNamespace(),
        exceptions=SimpleNamespace(),
    )

    queue = await service.list_queue(uuid4())

    assert len(queue) == document_count
    assert database.executed == ["documents"]
    assert repository.calls == ["list_by_documents"]


@pytest.mark.asyncio
async def test_queue_reuses_computed_decision_when_upsert_returns_no_rows():
    """A row the bulk upsert did not return must not trigger evaluate()."""

    class DroppingRepository(Repository):
        async def upsert_many(self, org_id, items):
            self.calls.append("upsert_many")
            self.upserted = items
            # Simulates a concurrent delete/RLS refusal between the insert and
            # the returning clause: the decisions were still computed.
            return []

    database = Database(40)
    repository = DroppingRepository(database, has_authorizations=False)
    service = PaymentAuthorizationService(
        db=database,
        repository=repository,
        vendors=SimpleNamespace(),
        exceptions=SimpleNamespace(),
    )

    async def fail_evaluate(**_kwargs):  # pragma: no cover - regression path
        raise AssertionError("the queue must not re-evaluate rows individually")

    service.evaluate = fail_evaluate

    queue = await service.list_queue(uuid4())

    assert len(queue) == 40
    # Still page rows, one vendor lookup and one exception lookup.
    assert database.executed == ["documents", "vendors", "invoice_exceptions"]
    assert repository.calls == ["list_by_documents", "upsert_many"]
    assert {item["authorization_status"] for item in queue} == {
        PaymentAuthorizationStatus.BLOCKED.value
    }
    assert queue[0]["blocked_reasons"]


@pytest.mark.asyncio
async def test_queue_without_stored_authorizations_evaluates_in_batches():
    database = Database(40)
    repository = Repository(database, has_authorizations=False)
    service = PaymentAuthorizationService(
        db=database,
        repository=repository,
        vendors=SimpleNamespace(),
        exceptions=SimpleNamespace(),
    )

    queue = await service.list_queue(uuid4())

    assert len(queue) == 40
    # Page rows, one vendor lookup, one exception lookup.
    assert database.executed == ["documents", "vendors", "invoice_exceptions"]
    assert repository.calls == ["list_by_documents", "upsert_many"]
    assert len(repository.upserted) == 40
    # No vendor row means bank details are unverified, so every decision is
    # blocked exactly as the single-document evaluate path would decide.
    assert {item["authorization_status"] for item in queue} == {
        PaymentAuthorizationStatus.BLOCKED.value
    }
